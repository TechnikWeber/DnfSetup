"""Shared plumbing: child processes, fold-out sections, dnf progress and the
NVIDIA restart guard. Taken over from DnfPilot."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from importlib import resources

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QToolButton, QVBoxLayout, QWidget

CMD_ENV = {"LC_ALL": "C", "LANG": "C", "TERM": "dumb", "NO_COLOR": "1"}


def have(program: str) -> bool:
    return shutil.which(program) is not None


def pkexec_command(actions: list[str]) -> tuple[str, list[str]]:
    """pkexec + bash running the bundled helper. The helper travels as the -c
    argument: root cannot read files inside a user's FUSE-mounted AppImage."""
    script = resources.files(__package__).joinpath("helper.sh").read_text()
    bash = shutil.which("bash") or "/usr/bin/bash"
    return "pkexec", [bash, "-c", script, "dnfsetup-helper", *actions]


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(CMD_ENV)
    return env


class Runner(QObject):
    """One child process; emits its output line by line (stdout+stderr merged)."""
    line = Signal(str)
    finished = Signal(int, str)  # exit code, collected output

    def __init__(self, parent: QObject, program: str, args: list[str]):
        super().__init__(parent)
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        for k, v in CMD_ENV.items():
            env.insert(k, v)
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.setStandardInputFile(QProcess.nullDevice())
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._done)
        self.proc.errorOccurred.connect(self._error)
        self.program, self.args = program, args
        self._buf = ""
        self._all: list[str] = []
        self._ended = False

    def start(self):
        self.proc.start(self.program, self.args)

    def running(self) -> bool:
        return self.proc.state() != QProcess.NotRunning

    def _read(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self._buf += data.replace("\r", "\n")
        *lines, self._buf = self._buf.split("\n")
        for ln in lines:
            if ln.strip():
                self._all.append(ln)
                self.line.emit(ln)

    def _done(self, code: int, _status):
        if self._ended:
            return
        self._read()
        if self._buf.strip():
            self._all.append(self._buf)
            self.line.emit(self._buf)
        self._ended = True
        self.finished.emit(code, "\n".join(self._all))

    def _error(self, err):
        if err == QProcess.FailedToStart and not self._ended:
            self._ended = True
            msg = f"{self.program}: could not be started"
            self.line.emit(msg)
            self.finished.emit(127, msg)


class Fold(QWidget):
    """A clickable header that shows or hides one widget below it."""

    def __init__(self, title: str, body: QWidget, open_: bool, extra: QWidget | None = None):
        super().__init__()
        self.body = body
        self.btn = QToolButton(text=title, checkable=True, checked=open_)
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.btn.toggled.connect(self._toggle)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self.btn)
        head.addStretch()
        if extra:
            head.addWidget(extra)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(head)
        lay.addWidget(body)
        self._toggle(open_)

    def _toggle(self, on: bool):
        self.btn.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(on)
        # closed: only as tall as the header, so it leaves no empty gap behind
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred if on else QSizePolicy.Maximum)

    def set_title(self, title: str):
        self.btn.setText(title)

    def set_open(self, on: bool):
        self.btn.setChecked(on)



# ---------------------------------------------------------------- dnf progress

# "[ 65/151] Upgrading vim-enhanced-2:9.2. 100% | ..." -- the name column is
# cut to a fixed width, so the only reliable end marker is the percentage.
_COUNTER = re.compile(r"^\[\s*(\d+)/(\d+)\]\s+(.*?)(?:\s+\d+%.*)?$")
_FLATPAK_OP = re.compile(r"^(Updating|Installing|Uninstalling)\s+(\S+)")


@dataclass
class DnfProgress:
    """Turns dnf5 output lines into a 0..1 fraction plus a short label.

    dnf5 numbers every download (``[ 3/78] pkg``) and every transaction step
    (``[ 65/151] Upgrading pkg``). Downloads end with a ``Total`` row; after
    that the counter starts again for the RPM transaction. Downloads count for
    the first 40 %, installing for the rest.
    """
    phase: str = "refresh"  # refresh -> download -> install -> done
    fraction: float = 0.0
    label: str = ""
    dl_split: float = 0.4  # 1.0 for download-only runs (offline, system-upgrade)

    def feed(self, line: str) -> bool:
        """Feed one line; return True when fraction or label changed."""
        line = line.rstrip()
        if line.startswith("Repositories loaded"):
            self.phase, self.label = "resolve", "resolve"
            return True
        m = _COUNTER.match(line)
        if not m:
            if line.startswith("Complete!"):
                self.phase, self.fraction, self.label = "done", 1.0, "done"
                return True
            return False
        n, total, what = int(m.group(1)), max(int(m.group(2)), 1), m.group(3).strip()
        if what == "Total":
            self.phase, self.fraction = "install", self.dl_split
            self.label = "download-done"
            return True
        if self.phase in ("refresh", "resolve"):
            # first counter: downloads, unless dnf had everything cached and
            # went straight to "Verify package files"
            self.phase = "install" if what.startswith("Verify") else "download"
        if self.phase == "download":
            self.fraction = self.dl_split * n / total
            self.label = f"download {n}/{total}"
        else:
            self.fraction = self.dl_split + (1 - self.dl_split) * n / total
            self.label = f"install {n}/{total} {what}"
        return True



# ---------------------------------------------------------------- NVIDIA guard

def newest_kernel() -> str:
    """Release of the most recently installed kernel, e.g. "7.2.15-200.fc44.x86_64"."""
    if not have("rpm"):
        return ""
    try:
        out = subprocess.run(["rpm", "-q", "--last", "kernel-core"], capture_output=True,
                             text=True, env=child_env(), timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    first = out.split("\n", 1)[0].split()
    return first[0].removeprefix("kernel-core-") if first and first[0].startswith("kernel-core-") else ""


def nvidia_module_pending() -> bool:
    """True while akmods is still building the NVIDIA module for the newest
    kernel. Restarting then ends with a black screen."""
    if not have("rpm"):
        return False
    try:
        installed = subprocess.run(["rpm", "-qa", "akmod-nvidia*"], capture_output=True,
                                   text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False
    if not installed:
        return False
    try:
        busy = subprocess.run(["pgrep", "-f", "akmods"], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        busy = False
    if busy:
        return True
    kver = newest_kernel()
    if not kver or not have("modinfo"):
        return False
    try:
        return subprocess.run(["modinfo", "-k", kver, "-F", "version", "nvidia"],
                              capture_output=True, timeout=10).returncode != 0
    except (OSError, subprocess.SubprocessError):
        return False


