# Changelog

## [0.1.0] - 2026-11-11

First release, checked on Fedora 45.

- Checklist window with every post-install step, showing which ones are
  already done on this machine.
- Steps: system update, firmware (fwupd), RPM Fusion, full multimedia codecs,
  Intel and AMD video acceleration, NVIDIA driver with the branch picked from
  the card name (current, 580xx, 470xx), Flathub without filter, removing a
  duplicate user Flathub, fonts metric-compatible with the Microsoft core fonts, OBS Studio as RPM, DVD playback,
  fuse for older AppImages.
- One password prompt for everything ticked, progress bar, fold-out details.
- Restart button that stays locked while akmods builds the NVIDIA module.
- English and German interface.
- AppImage (Gear Lever / AppImageUpdate compatible), RPM and `install.sh`.
