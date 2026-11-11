#!/usr/bin/env bash
# Removes the menu entry, icons and command that install.sh added.
set -euo pipefail

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"

rm -f "$apps/dnfsetup.desktop" "$HOME/.local/bin/dnfsetup"
rm -f "$icons/scalable/apps/dnfsetup.svg" "$icons/256x256/apps/dnfsetup.png"

command -v update-desktop-database >/dev/null && update-desktop-database "$apps" 2>/dev/null || true
command -v kbuildsycoca6           >/dev/null && kbuildsycoca6 --noincremental 2>/dev/null || true
echo "Removed from the application menu."
