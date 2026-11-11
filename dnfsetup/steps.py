"""The setup steps and how to tell whether each one is still needed.

Everything here is plain Python (no Qt) so it can be unit-tested. Detection
reads a `Facts` snapshot; `gather_facts()` fills it from the running system.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

TARGET_RELEASE = 45  # the Fedora release these steps were checked on
BLOG_URL = "https://technikweber.github.io/2026/fedora-kde-nach-der-installation/"
RPMFUSION_SB_URL = "https://rpmfusion.org/Howto/Secure%20Boot"

ENV = {"LC_ALL": "C", "LANG": "C"}

# packages whose presence tells whether a step is done
PROBE_PACKAGES = [
    "rpmfusion-free-release", "rpmfusion-nonfree-release", "rpmfusion-free-appstream-data", "ffmpeg", "ffmpeg-free",
    "intel-media-driver", "mesa-va-drivers-freeworld", "mesa-vulkan-drivers-freeworld",
    "akmod-nvidia", "akmod-nvidia-580xx", "akmod-nvidia-470xx",
    "google-carlito-fonts", "google-crosextra-caladea-fonts", "obs-studio", "libdvdcss", "fuse", "fuse-libs",
]


# ---------------------------------------------------------------- facts

@dataclass
class Gpu:
    vendor: str  # intel / amd / nvidia
    name: str


@dataclass
class Facts:
    release: int = 0
    installed: set[str] = field(default_factory=set)
    gpus: list[Gpu] = field(default_factory=list)
    secure_boot: bool = False
    flathub_system: str = ""  # "", "ok", "filtered", "disabled"
    flathub_user: bool = False
    flathub_user_apps: int = 0
    updates: int | None = None  # dnf check-upgrade; None = unknown
    firmware_updates: int | None = None
    have: set[str] = field(default_factory=set)


_LSPCI = re.compile(r"^\S+\s+(VGA compatible controller|3D controller|Display controller)\s*\[[0-9a-f]{4}\]:\s*(.*?)\s*\[([0-9a-f]{4}):[0-9a-f]{4}\]", re.I)
VENDORS = {"8086": "intel", "1002": "amd", "10de": "nvidia"}


def parse_lspci(text: str) -> list[Gpu]:
    """Parse `lspci -nn` and keep graphics devices of the three big vendors."""
    gpus = []
    for line in text.splitlines():
        m = _LSPCI.match(line)
        if m and m.group(3).lower() in VENDORS:
            gpus.append(Gpu(VENDORS[m.group(3).lower()], m.group(2)))
    return gpus


def nvidia_series(name: str) -> str:
    """Which RPM Fusion driver branch fits an NVIDIA card name from lspci.

    current: RTX 20xx and newer, GTX 16xx, RTX/Ax000 workstation cards
    580xx:   Maxwell + Pascal: GTX 9xx, GTX/GT 10xx, MX1xx/2xx/3xx, Quadro M/P
    470xx:   Kepler: GeForce 6xx/7xx, Quadro K
    "":      unknown, let the user pick
    """
    n = name.upper()
    bracket = re.findall(r"\[([^\]]+)\]", name)
    if bracket:  # "GP106 [GeForce GTX 1060 6GB]" -> the marketing name
        n = bracket[-1].upper()
    if re.search(r"\bRTX\b|\bGTX 16\d\d\b|\bA\d{3,4}\b|\bL\d{1,2}\b|\bH\d{3}\b", n):
        return "current"
    if re.search(r"\bGTX 9\d\d\b|\bGTX? 10\d\d\b|\bMX ?[123]\d\d\b|\bQUADRO [MP]\d", n):
        return "580xx"
    if re.search(r"\bGTX? [67]\d\d\b|\bGT [67]\d\d\b|\bQUADRO K\d", n):
        return "470xx"
    return ""


def parse_flatpak_remotes(text: str) -> tuple[str, bool]:
    """From `flatpak remotes --columns=name,options,filter`: state of the system
    Flathub and whether a duplicate user Flathub exists."""
    system, user = "", False
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 2 or cols[0].strip() != "flathub":
            continue
        options = cols[1]
        filt = cols[2].strip() if len(cols) > 2 else "-"
        if "user" in options:
            user = True
        elif "system" in options:
            if "disabled" in options:
                system = "disabled"
            elif filt not in ("", "-"):
                system = "filtered"
            else:
                system = "ok"
    return system, user


def parse_rpm_installed(text: str) -> set[str]:
    """`rpm -q --qf '%{NAME}\\n' a b c` prints names, or 'package x is not installed'."""
    return {ln.strip() for ln in text.splitlines() if ln.strip() and " " not in ln.strip()}


def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess | None:
    try:
        env = dict(__import__("os").environ, **ENV)
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError):
        return None


def current_release() -> int:
    try:
        m = re.search(r'^VERSION_ID="?(\d+)', Path("/etc/os-release").read_text(), re.M)
    except OSError:
        return 0
    return int(m.group(1)) if m else 0


def gather_facts() -> Facts:
    """Everything quick. dnf check-upgrade and fwupd are slow and are filled in
    by the window afterwards (see window.py)."""
    f = Facts(release=current_release())
    f.have = {p for p in ("dnf", "rpm", "flatpak", "fwupdmgr", "lspci", "mokutil", "pkexec") if shutil.which(p)}
    if "rpm" in f.have:
        r = _run(["rpm", "-q", "--qf", "%{NAME}\\n", *PROBE_PACKAGES])
        if r:
            f.installed = parse_rpm_installed(r.stdout)
    if "lspci" in f.have:
        r = _run(["lspci", "-nn"])
        if r:
            f.gpus = parse_lspci(r.stdout)
    if "mokutil" in f.have:
        r = _run(["mokutil", "--sb-state"])
        f.secure_boot = bool(r and "SecureBoot enabled" in r.stdout)
    if "flatpak" in f.have:
        r = _run(["flatpak", "remotes", "--columns=name,options,filter"])
        if r:
            f.flathub_system, f.flathub_user = parse_flatpak_remotes(r.stdout)
        if f.flathub_user:
            r = _run(["flatpak", "list", "--user", "--columns=origin"])
            if r:
                f.flathub_user_apps = sum(ln.strip() == "flathub" for ln in r.stdout.splitlines())
    return f


def count_check_upgrade(code: int, text: str) -> int | None:
    if code == 0:
        return 0
    if code != 100:
        return None
    return sum(bool(re.match(r"^\S+\.\S+\s+\S+\s+\S+$", ln.rstrip())) for ln in text.splitlines())


def count_fwupd(text: str) -> int | None:
    try:
        return len(json.loads(text).get("Devices", []))
    except ValueError:
        return None


# ---------------------------------------------------------------- steps

DONE, TODO, NA, UNKNOWN = "done", "todo", "na", "unknown"


@dataclass
class Step:
    id: str
    group: str  # "basics", "graphics", "extras"
    title: str
    text: str
    action: str  # helper action; "user:..." runs without root
    requires: tuple[str, ...] = ()
    reboot: bool = False
    default: bool = True  # ticked when still to do
    state: str = UNKNOWN
    note: str = ""  # extra line under the description (warnings)
    choices: tuple[str, ...] = ()  # NVIDIA driver branches
    args: dict = field(default_factory=dict)  # placeholders in text/note

    @property
    def root(self) -> bool:
        return not self.action.startswith("user:")


def build_steps(f: Facts) -> list[Step]:
    """All steps that apply to this machine, with their current state."""
    inst = f.installed
    rf = {"rpmfusion-free-release", "rpmfusion-nonfree-release"} <= inst
    steps: list[Step] = []

    def add(step: Step, state: str):
        step.state = state
        steps.append(step)

    add(Step("upgrade", "basics", "Update the system",
             "dnf upgrade --refresh – everything else builds on an up-to-date system.", "upgrade"),
        UNKNOWN if f.updates is None else (DONE if f.updates == 0 else TODO))
    if "fwupdmgr" in f.have:
        add(Step("firmware", "basics", "Update firmware",
                 "BIOS/UEFI, SSD, Thunderbolt and more via fwupd, as far as the vendor takes part.",
                 "firmware", reboot=True),
            UNKNOWN if f.firmware_updates is None else (DONE if f.firmware_updates == 0 else TODO))
    add(Step("rpmfusion", "basics", "Enable RPM Fusion",
             "The source for codecs and proprietary drivers (free + nonfree).", "rpmfusion"),
        DONE if rf and "rpmfusion-free-appstream-data" in inst else TODO)
    add(Step("codecs", "basics", "Full multimedia codecs",
             "Swap ffmpeg-free for the full FFmpeg and add the GStreamer plugins: H.264, H.265, AAC in Firefox, VLC, Kdenlive.",
             "codecs", requires=("rpmfusion",), reboot=True),
        DONE if "ffmpeg" in inst else TODO)

    # graphics: one step per vendor that is actually in the machine
    vendors = {g.vendor for g in f.gpus}
    if "intel" in vendors:
        add(Step("intel", "graphics", "Intel video acceleration",
                 "intel-media-driver: hardware video decoding for Intel graphics from about 2014 on.",
                 "intel", requires=("rpmfusion",)),
            DONE if "intel-media-driver" in inst else TODO)
    if "amd" in vendors:
        add(Step("amd", "graphics", "AMD video acceleration",
                 "The freeworld Mesa drivers with H.264/H.265 decoding and encoding.",
                 "amd", requires=("rpmfusion",)),
            DONE if "mesa-va-drivers-freeworld" in inst else TODO)
    for g in f.gpus:
        if g.vendor != "nvidia":
            continue
        series = nvidia_series(g.name)
        have = next((s for s in ("current", "580xx", "470xx")
                     if ("akmod-nvidia" if s == "current" else f"akmod-nvidia-{s}") in inst), "")
        note = ""
        if f.secure_boot:
            note = "Secure Boot is on: the driver module has to be signed, otherwise the screen stays black."
        step = Step("nvidia", "graphics", "NVIDIA driver",
                    "{gpu}. Proprietary driver with video acceleration; the kernel module is built in the "
                    "background afterwards (up to 5 minutes) – do not restart before it is done.",
                    f"nvidia:{have or series or 'current'}", requires=("rpmfusion",), reboot=True,
                    default=bool(series) and not f.secure_boot, note=note,
                    choices=("current", "580xx", "470xx"), args={"gpu": g.name})
        add(step, DONE if have else TODO)
        break

    if "flatpak" in f.have and f.flathub_system:
        add(Step("flathub", "basics", "Flathub without filter",
                 "Fedora ships Flathub with a filter that only shows a selection. This shows all apps.",
                 "flathub-nofilter"),
            DONE if f.flathub_system == "ok" else TODO)
    if f.flathub_user:
        step = Step("flathub-user", "basics", "Remove the duplicate Flathub",
                    "Flathub is set up twice (system and user), so Discover shows every app twice.",
                    "user:flathub-user-remove")
        if f.flathub_user_apps:
            step.note = "{n} app(s) are installed from the user Flathub – reinstall them system-wide first."
            step.args = {"n": f.flathub_user_apps}
            add(step, NA)
        else:
            add(step, TODO)

    add(Step("msfonts", "extras", "Fonts for Word documents",
             "Free fonts with the exact sizes of Arial, Times New Roman, Courier, Calibri and Cambria, "
             "so Word documents keep their layout.", "msfonts", default=False),
        DONE if {"google-carlito-fonts", "google-crosextra-caladea-fonts"} <= inst else TODO)
    add(Step("obs", "extras", "OBS Studio as RPM",
             "With NVIDIA the RPM gets NVENC without extra packages (the Flatpak does not).", "obs", default=False),
        DONE if "obs-studio" in inst else TODO)
    add(Step("dvd", "extras", "Play DVDs",
             "libdvdcss from RPM Fusion tainted. Judge the legal situation in your country yourself.",
             "dvd", requires=("rpmfusion",), default=False),
        DONE if "libdvdcss" in inst else TODO)
    add(Step("fuse2", "extras", "Older AppImages",
             "fuse + fuse-libs for AppImages that stop with a libfuse.so.2 error.", "fuse2", default=False),
        DONE if {"fuse", "fuse-libs"} <= inst else TODO)
    return steps


def order_actions(steps: list[Step], selected: set[str]) -> tuple[list[str], list[str]]:
    """Root and user actions for the selected step ids, in list order.
    Required steps that are still to do are pulled in automatically."""
    by_id = {s.id: s for s in steps}
    want = set(selected)
    for sid in list(selected):
        for req in by_id[sid].requires if sid in by_id else ():
            if req in by_id and by_id[req].state != DONE:
                want.add(req)
    chosen = [s for s in steps if s.id in want]
    root = [s.action for s in chosen if s.root]
    user = [s.action.removeprefix("user:") for s in chosen if not s.root]
    return root, user
