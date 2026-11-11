"""Renders docs/screenshot.png: the real window with demo facts of a fresh
Fedora 45 install (Intel + NVIDIA laptop), independent of this machine.

    DNFSETUP_LANG=en python3 tools/screenshot.py    # needs a desktop session
"""
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dnfsetup import steps, window  # noqa: E402

DEMO = steps.Facts(
    release=45, have={"dnf", "rpm", "flatpak", "fwupdmgr", "lspci", "pkexec"},
    gpus=[steps.Gpu("intel", "Intel Corporation Alder Lake-P GT2 [Iris Xe Graphics]"),
          steps.Gpu("nvidia", "NVIDIA Corporation GA107M [GeForce RTX 3050 Mobile]")],
    flathub_system="filtered", updates=0, firmware_updates=1, installed={"fuse", "fuse-libs"},
)
steps.gather_facts = lambda: DEMO
window.MainWindow.refresh = lambda self: (self._show_version(), self._render(), self._finish_refresh())

app = QApplication(sys.argv[:1])
app.setDesktopFileName("dnfsetup")
win = window.MainWindow()
win.facts = DEMO
win._show_version()
win._render()
win._finish_refresh()
win.resize(760, 860)
win.show()


def shoot():
    win.grab().save(str(ROOT / "docs" / "screenshot.png"))
    app.quit()


QTimer.singleShot(800, shoot)
app.exec()
