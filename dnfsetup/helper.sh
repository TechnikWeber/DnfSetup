#!/usr/bin/env bash
# Root helper for DnfSetup. Runs through pkexec, so there is one password
# prompt for everything that was ticked. Every argument is one action,
# executed in order; "@@DS" marker lines let the GUI follow along.
#
# The commands are the ones from
# https://technikweber.github.io/2026/fedora-kde-nach-der-installation/
# checked on Fedora 45.

export LC_ALL=C LANG=C TERM=dumb NO_COLOR=1

marker() { printf '@@DS %s\n' "$*"; }

fedora="$(rpm -E %fedora)"

run_action() {
    case "$1" in
        upgrade)
            dnf upgrade --refresh -y ;;
        firmware)
            fwupdmgr refresh --force || true
            fwupdmgr update -y --no-reboot-check --no-unreported-check
            local fw=$?
            # 2 = nothing to update
            [ "$fw" -eq 2 ] && fw=0
            return "$fw" ;;
        rpmfusion)
            dnf install -y \
                "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$fedora.noarch.rpm" \
                "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$fedora.noarch.rpm" &&
            # app metadata so Discover lists RPM Fusion software. The usual
            # "dnf upgrade @core" does this only when the core group is marked
            # installed, which dnf5 systems often do not have.
            dnf install -y rpmfusion-free-appstream-data rpmfusion-nonfree-appstream-data ;;
        codecs)
            dnf swap -y ffmpeg-free ffmpeg --allowerasing &&
            dnf install -y @multimedia --setopt=install_weak_deps=False \
                --exclude=PackageKit-gstreamer-plugin ;;
        intel)
            dnf install -y intel-media-driver ;;
        amd)
            dnf install -y mesa-va-drivers-freeworld &&
            dnf swap -y mesa-vulkan-drivers mesa-vulkan-drivers-freeworld ;;
        nvidia:*)
            local series="${1#*:}" sfx=""
            case "$series" in
                current) sfx="" ;;
                580xx|470xx) sfx="-$series" ;;
                *) echo "unknown NVIDIA series: $series" >&2; return 2 ;;
            esac
            dnf install -y "akmod-nvidia$sfx" "xorg-x11-drv-nvidia$sfx-cuda" libva-nvidia-driver ;;
        flathub-nofilter)
            flatpak remote-modify --system --no-filter --enable flathub ;;
        msfonts)
            # metric-compatible with Arial/Times/Courier (Liberation), Calibri
            # (Carlito) and Cambria (Caladea). The old msttcore-fonts-installer
            # RPM has no digests and is refused by rpm on Fedora 45.
            dnf install -y liberation-sans-fonts liberation-serif-fonts liberation-mono-fonts \
                google-carlito-fonts google-crosextra-caladea-fonts ;;
        obs)
            dnf install -y obs-studio ;;
        dvd)
            dnf install -y rpmfusion-free-release-tainted &&
            dnf install -y libdvdcss ;;
        fuse2)
            dnf install -y fuse fuse-libs ;;
        *)
            echo "unknown action: $1" >&2; return 2 ;;
    esac
}

for action in "$@"; do
    marker "step $action"
    run_action "$action" </dev/null 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        marker "fail $action $rc"
        exit "$rc"
    fi
    marker "done $action"
done
marker "finished"
