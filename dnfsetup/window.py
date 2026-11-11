"""The main window: a checklist of setup steps, progress bar, details, buttons."""
from __future__ import annotations

from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase, QIcon
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from . import steps as S
from .i18n import tr
from .icon import app_icon
from .ui import DnfProgress, Fold, Runner, have, nvidia_module_pending, pkexec_command

GROUPS = (("basics", "Basics"), ("graphics", "Graphics"), ("extras", "If needed"))
NVIDIA_LABELS = {
    "current": "RTX 20xx, GTX 16xx and newer",
    "580xx": "GTX 9xx / 10xx, MX (580xx)",
    "470xx": "GeForce 600 / 700 (470xx)",
}
NO_DNF = {"flathub-nofilter", "firmware"}  # helper actions without dnf output


class StepRow(QFrame):
    def __init__(self, step: S.Step, checked: bool):
        super().__init__()
        self.step = step
        self.setObjectName("row")
        self.setStyleSheet("#row { border-bottom: 1px solid palette(midlight); }")
        self.box = QCheckBox(tr(step.title))
        f = self.box.font()
        f.setBold(True)
        self.box.setFont(f)
        todo = step.state in (S.TODO, S.UNKNOWN)
        self.box.setChecked(checked and todo)
        self.box.setEnabled(todo and step.state != S.NA)
        desc = QLabel(tr(step.text, **step.args))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: palette(placeholder-text);")
        desc.setContentsMargins(24, 0, 0, 0)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(2)
        top = QHBoxLayout()
        top.addWidget(self.box, 1)
        self.combo = None
        if step.choices and todo:
            self.combo = QComboBox()
            for c in step.choices:
                self.combo.addItem(tr(NVIDIA_LABELS[c]), c)
            cur = step.action.split(":", 1)[1]
            self.combo.setCurrentIndex(max(0, step.choices.index(cur) if cur in step.choices else 0))
            top.addWidget(self.combo)
        self.state = QLabel(self._state_text(step.state))
        top.addWidget(self.state)
        lay.addLayout(top)
        lay.addWidget(desc)
        if step.note:
            note = QLabel("⚠ " + tr(step.note, **step.args))
            note.setWordWrap(True)
            note.setContentsMargins(24, 0, 0, 0)
            note.setStyleSheet("color: #d35400;")
            lay.addWidget(note)

    @staticmethod
    def _state_text(state: str) -> str:
        return {
            S.DONE: "✓ " + tr("done"),
            S.TODO: tr("to do"),
            S.NA: tr("not possible"),
            S.UNKNOWN: tr("checking…"),
        }[state]

    def action(self) -> str:
        if self.combo is not None:
            return f"nvidia:{self.combo.currentData()}"
        return self.step.action


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DnfSetup")
        self.setWindowIcon(app_icon())
        self.resize(760, 760)
        self.runner: Runner | None = None
        self.in_job = False
        self.facts = S.Facts()
        self.steps: list[S.Step] = []
        self.rows: dict[str, StepRow] = {}
        self.selection: dict[str, bool] = {}
        self.ran_reboot_step = False
        self.guard_timer = QTimer(self, interval=15000)
        self.guard_timer.timeout.connect(self._update_guard)
        self._build()
        self.refresh()

    # ------------------------------------------------------------ layout
    def _build(self):
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(56, 56))
        title = QLabel("DnfSetup")
        f = title.font()
        f.setPointSizeF(f.pointSizeF() * 1.5)
        f.setBold(True)
        title.setFont(f)
        self.status = QLabel(tr("Checking the system…"))
        self.status.setWordWrap(True)
        text = QVBoxLayout()
        text.addWidget(title)
        text.addWidget(self.status)
        head = QHBoxLayout()
        head.addWidget(icon)
        head.addSpacing(8)
        head.addLayout(text, 1)

        self.version_note = QLabel()
        self.version_note.setWordWrap(True)
        self.version_note.setObjectName("banner")
        self.version_note.setStyleSheet(
            "#banner { background: rgba(61, 174, 233, 0.15); border: 1px solid rgba(61, 174, 233, 0.6);"
            " border-radius: 6px; padding: 8px; }")
        self.version_note.setVisible(False)

        self.list_host = QWidget()
        self.list_lay = QVBoxLayout(self.list_host)
        self.list_lay.setContentsMargins(0, 0, 8, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.list_host)

        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.step_label = QLabel(tr("Ready."))
        self.log = QPlainTextEdit(readOnly=True)
        self.log.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.log.setMaximumBlockCount(20000)
        self.log.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_fold = Fold(tr("Details"), self.log, False)

        self.btn_blog = QPushButton(QIcon.fromTheme("help-about"), tr("Background"))
        self.btn_blog.setToolTip(S.BLOG_URL)
        self.btn_blog.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(S.BLOG_URL)))
        self.btn_check = QPushButton(QIcon.fromTheme("view-refresh"), tr("Check again"))
        self.btn_check.clicked.connect(self.refresh)
        self.btn_reboot = QPushButton(QIcon.fromTheme("system-reboot"), tr("Restart"))
        self.btn_reboot.clicked.connect(self.ask_reboot)
        self.btn_apply = QPushButton(QIcon.fromTheme("dialog-ok-apply"), tr("Set up selected"))
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self.apply)
        foot = QHBoxLayout()
        foot.addWidget(self.btn_blog)
        foot.addWidget(self.btn_check)
        foot.addStretch()
        foot.addWidget(self.btn_reboot)
        foot.addWidget(self.btn_apply)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        lay.addLayout(head)
        lay.addWidget(self.version_note)
        if not have("pkexec"):
            lay.addWidget(QLabel(tr("pkexec is missing (package polkit), so nothing can be set up from here.")))
        lay.addWidget(scroll, 4)
        lay.addWidget(self.bar)
        lay.addWidget(self.step_label)
        lay.addWidget(self.log_fold, 1)
        lay.addLayout(foot)

    # ------------------------------------------------------------ helpers
    def _log(self, text: str):
        self.log.appendPlainText(text)

    def _run(self, cmd: tuple[str, list[str]], on_line, on_done, show: str | None = None):
        program, args = cmd
        self._log(f"$ {show or ' '.join([program, *args])}")
        r = Runner(self, program, args)
        r.line.connect(self._log)
        if on_line:
            r.line.connect(on_line)

        def done(code, out):
            self.runner = None
            r.deleteLater()
            on_done(code, out)

        r.finished.connect(done)
        self.runner = r
        r.start()

    def _set_progress(self, fraction: float | None):
        if fraction is None:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(max(0.0, min(1.0, fraction)) * 1000))

    def _busy(self, busy: bool):
        for w in (self.btn_check, self.btn_reboot, self.btn_apply, self.list_host):
            w.setEnabled(not busy)
        if not busy:
            self._update_guard()
            self._count_selected()

    # ------------------------------------------------------------ detection
    def refresh(self):
        if self.runner:
            return
        self._busy(True)
        self.status.setText(tr("Checking the system…"))
        self._set_progress(None)
        self._remember_selection()
        self.facts = S.gather_facts()
        self._show_version()
        self._render()
        self._busy(True)

        def fw_done(_code, out):
            self.facts.firmware_updates = S.count_fwupd(out)
            self._finish_refresh()

        def dnf_done(code, out):
            self.facts.updates = S.count_check_upgrade(code, out)
            if "fwupdmgr" in self.facts.have:
                self._run(("fwupdmgr", ["get-updates", "--json", "--no-unreported-check"]), None, fw_done)
            else:
                self._finish_refresh()

        if "dnf" in self.facts.have:
            self._run(("dnf", ["check-upgrade", "--refresh", "--assumeno"]), None, dnf_done)
        else:
            self._finish_refresh()

    def _finish_refresh(self):
        self._remember_selection()
        self._render()
        todo = sum(s.state == S.TODO for s in self.steps)
        self.status.setText(tr("Everything is set up.") if not todo else
                            tr("{n} of {t} steps still open.", n=todo, t=len(self.steps)))
        self.step_label.setText(tr("Ready."))
        self._set_progress(0)
        self._busy(False)

    def _show_version(self):
        rel, target = self.facts.release, S.TARGET_RELEASE
        if not rel:
            text = tr("This does not look like Fedora – the steps will most likely not work here.")
        elif rel < target:
            text = tr("These steps were checked on Fedora {t}; you are on Fedora {r}. Most of them work the same, but upgrade first if you can – DnfPilot does that in a few clicks.", t=target, r=rel)
        elif rel > target:
            text = tr("These steps were checked on Fedora {t}; you are on Fedora {r}. Package names may have changed – look at the details if a step fails.", t=target, r=rel)
        else:
            text = ""
        self.version_note.setText(text)
        self.version_note.setVisible(bool(text))

    def _remember_selection(self):
        for sid, row in self.rows.items():
            if row.box.isEnabled():
                self.selection[sid] = row.box.isChecked()

    def _render(self):
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.steps = S.build_steps(self.facts)
        self.rows = {}
        for key, label in GROUPS:
            group = [s for s in self.steps if s.group == key]
            if not group:
                continue
            head = QLabel(tr(label))
            f = head.font()
            f.setPointSizeF(f.pointSizeF() * 1.15)
            f.setBold(True)
            head.setFont(f)
            head.setContentsMargins(0, 10, 0, 2)
            self.list_lay.addWidget(head)
            for step in group:
                row = StepRow(step, self.selection.get(step.id, step.default))
                row.box.toggled.connect(lambda on, sid=step.id: self._toggled(sid, on))
                self.rows[step.id] = row
                self.list_lay.addWidget(row)
        self.list_lay.addStretch()
        self._count_selected()

    def _toggled(self, sid: str, on: bool):
        """Keep requirements consistent: ticking codecs ticks RPM Fusion, and
        unticking RPM Fusion unticks everything that needs it."""
        by_id = {s.id: s for s in self.steps}
        if on:
            for req in by_id[sid].requires:
                row = self.rows.get(req)
                if row and row.box.isEnabled() and not row.box.isChecked():
                    row.box.setChecked(True)
        else:
            for s in self.steps:
                row = self.rows.get(s.id)
                if sid in s.requires and row and row.box.isChecked() and by_id[sid].state != S.DONE:
                    row.box.setChecked(False)
        self._count_selected()

    def _selected(self) -> list[str]:
        return [sid for sid, row in self.rows.items() if row.box.isEnabled() and row.box.isChecked()]

    def _count_selected(self):
        n = len(self._selected())
        self.btn_apply.setText(tr("Set up selected ({n})", n=n))
        self.btn_apply.setEnabled(n > 0 and not self.in_job and not self.runner)

    # ------------------------------------------------------------ apply
    def apply(self):
        if self.runner:
            return
        chosen = self._selected()
        if not chosen:
            return
        # the NVIDIA row may have a different branch picked in its combo box
        for s in self.steps:
            if s.id in self.rows:
                s.action = self.rows[s.id].action()
        root, user = S.order_actions(self.steps, set(chosen))
        names = [tr(s.title) for s in self.steps if s.action in root or s.action.removeprefix("user:") in user]
        box = QMessageBox(QMessageBox.Question, "DnfSetup",
                          tr("These steps will run now:") + "\n\n" + "\n".join(f"  • {n}" for n in names) + "\n\n" +
                          tr("You will be asked for your password once. This can take a while; the details show every command."),
                          parent=self)
        go = box.addButton(tr("Start"), QMessageBox.AcceptRole)
        box.addButton(tr("Cancel"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not go:
            return
        self.in_job = True
        self._busy(True)
        self.ran_reboot_step = any(s.reboot for s in self.steps if s.action in root)
        self.total = len(root) + len(user)
        self.index = 0
        if root:
            self._run_root(root, user)
        else:
            self._run_user(user)

    def _title_for(self, action: str) -> str:
        step = next((s for s in self.steps if s.action == action or s.action == "user:" + action), None)
        return tr(step.title) if step else action

    def _show_step(self, action: str, sub: str = "", fraction: float = 0.0):
        what = self._title_for(action) + (" – " + sub if sub else "")
        self.step_label.setText(tr("Step {i} of {n}: {what}", i=self.index, n=self.total, what=what))
        self._set_progress((self.index - 1 + fraction) / max(self.total, 1))

    def _run_root(self, actions: list[str], user: list[str]):
        self.step_label.setText(tr("Waiting for your password…"))
        self._set_progress(None)
        state = {"action": None, "prog": DnfProgress()}

        def on_line(ln: str):
            if ln.startswith("@@DS "):
                parts = ln.split()
                if parts[1] == "step":
                    self.index += 1
                    state["action"], state["prog"] = parts[2], DnfProgress()
                    self._show_step(parts[2])
                return
            act = state["action"]
            if act and act.split(":")[0] not in NO_DNF and state["prog"].feed(ln):
                p = state["prog"]
                sub = tr("Downloading") if p.phase == "download" else tr("Installing") if p.phase == "install" else ""
                self._show_step(act, sub, p.fraction)

        def done(code, out):
            if code == 0:
                if user:
                    self._run_user(user)
                else:
                    self._job_done()
                return
            if code == 126:
                self._finish(tr("Cancelled – no password was entered."))
            elif code == 127 and "@@DS" not in out:
                self._finish(tr("Not authorized to change the system."))
            else:
                failed = next((ln.split()[2] for ln in out.splitlines() if ln.startswith("@@DS fail")), state["action"] or "")
                self._failed(failed, code)

        self._run(pkexec_command(actions), on_line, done, show="pkexec dnfsetup-helper " + " ".join(actions))

    def _run_user(self, actions: list[str]):
        if not actions:
            self._job_done()
            return
        action, rest = actions[0], actions[1:]
        self.index += 1
        self._show_step(action)
        cmds = {"flathub-user-remove": ("flatpak", ["remote-delete", "--user", "flathub"])}

        def done(code, _out):
            if code != 0:
                self._failed(action, code)
            else:
                self._run_user(rest)

        self._run(cmds[action], None, done)

    def _failed(self, action: str, code: int):
        self.log_fold.set_open(True)
        what = self._title_for(action)
        self._finish(tr("Failed: {what} (exit code {rc}).", what=what, rc=code))
        QMessageBox.critical(self, "DnfSetup", tr(
            "{what} failed. The steps before it are done. The details below show the original message – "
            "often it is a network hiccup or RPM Fusion lagging behind a new Fedora release; try again later.",
            what=what))
        self.refresh()

    def _finish(self, text: str):
        self.in_job = False
        self.step_label.setText(text)
        self._set_progress(0)
        self._busy(False)

    def _job_done(self):
        self.in_job = False
        self._set_progress(1)
        self.step_label.setText(tr("Done."))
        self._busy(False)
        if self.ran_reboot_step:
            self._offer_reboot()
        self.refresh()

    # ------------------------------------------------------------ restart
    def _update_guard(self):
        pending = nvidia_module_pending()
        if pending:
            self.btn_reboot.setEnabled(False)
            self.btn_reboot.setToolTip(tr("The NVIDIA driver is still being built. Restarting now would end with a black screen."))
            self.step_label.setText(tr("The NVIDIA driver is being built in the background – the Restart button unlocks when it is ready."))
            self.guard_timer.start()
        else:
            self.guard_timer.stop()
            self.btn_reboot.setToolTip("")
            self.btn_reboot.setEnabled(not self.in_job and not self.runner)
        return pending

    def _offer_reboot(self):
        if self._update_guard():
            QMessageBox.information(self, "DnfSetup", tr(
                "Done. The NVIDIA driver is still being built for your kernel – wait until the Restart button unlocks (up to 5 minutes), then restart."))
            return
        box = QMessageBox(QMessageBox.Question, "DnfSetup",
                          tr("Done. Some changes only take effect after a restart. Restart now?"), parent=self)
        go = box.addButton(tr("Restart now"), QMessageBox.AcceptRole)
        box.addButton(tr("Later"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is go:
            QProcess.startDetached("systemctl", ["reboot"])

    def ask_reboot(self):
        if self._update_guard():
            return
        box = QMessageBox(QMessageBox.Question, tr("Restart"),
                          tr("Restart the computer now? Save your open work first."), parent=self)
        go = box.addButton(tr("Restart now"), QMessageBox.AcceptRole)
        box.addButton(tr("Cancel"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is go:
            QProcess.startDetached("systemctl", ["reboot"])

    def closeEvent(self, ev):
        if self.in_job:
            QMessageBox.warning(self, "DnfSetup", tr(
                "Setup is running. Please wait until it has finished – stopping dnf halfway can damage the system."))
            ev.ignore()
            return
        if self.runner and self.runner.running():
            self.runner.proc.kill()  # only a check
        ev.accept()
