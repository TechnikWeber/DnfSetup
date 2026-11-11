"""Tiny translation table: English is the key, German follows the system locale.

Set DNFSETUP_LANG=en or =de to override.
"""
from __future__ import annotations

import locale
import os

DE = {
    # window
    "Checking the system…": "System wird geprüft …",
    "Ready.": "Bereit.",
    "Details": "Details",
    "Background": "Hintergrund",
    "Check again": "Erneut prüfen",
    "Restart": "Neu starten",
    "Set up selected": "Ausgewählte einrichten",
    "Set up selected ({n})": "Ausgewählte einrichten ({n})",
    "Start": "Starten",
    "Cancel": "Abbrechen",
    "Step {i} of {n}: {what}": "Schritt {i} von {n}: {what}",
    "Waiting for your password…": "Warte auf dein Passwort …",
    "Downloading": "Download",
    "Installing": "Installation",
    "Failed: {what} (exit code {rc}).": "Fehlgeschlagen: {what} (Exit-Code {rc}).",
    "{what} failed. The steps before it are done. The details below show the original message – often it is a network hiccup or RPM Fusion lagging behind a new Fedora release; try again later.":
        "{what} ist fehlgeschlagen. Die Schritte davor sind erledigt. Die Details unten zeigen die Originalmeldung – oft ist es ein Netzaussetzer oder RPM Fusion hinkt einer neuen Fedora-Version hinterher; später noch einmal versuchen.",
    "Done.": "Fertig.",
    "Done. Some changes only take effect after a restart. Restart now?":
        "Fertig. Einige Änderungen wirken erst nach einem Neustart. Jetzt neu starten?",
    "Restart now": "Jetzt neu starten",
    "Later": "Später",
    "Restart the computer now? Save your open work first.":
        "Den Computer jetzt neu starten? Speichere vorher deine offene Arbeit.",
    "done": "erledigt",
    "to do": "offen",
    "not possible": "nicht möglich",
    "checking…": "wird geprüft …",
    "Everything is set up.": "Alles ist eingerichtet.",
    "{n} of {t} steps still open.": "{n} von {t} Schritten sind noch offen.",
    "This does not look like Fedora – the steps will most likely not work here.":
        "Das sieht nicht nach Fedora aus – die Schritte funktionieren hier sehr wahrscheinlich nicht.",
    "These steps were checked on Fedora {t}; you are on Fedora {r}. Most of them work the same, but upgrade first if you can – DnfPilot does that in a few clicks.":
        "Diese Schritte sind für Fedora {t} geprüft; du nutzt Fedora {r}. Die meisten funktionieren gleich, aber upgrade wenn möglich zuerst – DnfPilot erledigt das mit ein paar Klicks.",
    "These steps were checked on Fedora {t}; you are on Fedora {r}. Package names may have changed – look at the details if a step fails.":
        "Diese Schritte sind für Fedora {t} geprüft; du nutzt Fedora {r}. Paketnamen können sich geändert haben – bei einem Fehler in die Details schauen.",
    "These steps will run now:": "Diese Schritte laufen jetzt:",
    "You will be asked for your password once. This can take a while; the details show every command.":
        "Dein Passwort wird einmal abgefragt. Das kann eine Weile dauern; die Details zeigen jeden Befehl.",
    "Cancelled – no password was entered.": "Abgebrochen – kein Passwort eingegeben.",
    "Not authorized to change the system.": "Keine Berechtigung, das System zu ändern.",
    "The NVIDIA driver is still being built. Restarting now would end with a black screen.":
        "Der NVIDIA-Treiber wird noch gebaut. Ein Neustart jetzt endet mit schwarzem Bildschirm.",
    "The NVIDIA driver is being built in the background – the Restart button unlocks when it is ready.":
        "Der NVIDIA-Treiber wird im Hintergrund gebaut – der Neustart-Knopf wird frei, sobald er fertig ist.",
    "Done. The NVIDIA driver is still being built for your kernel – wait until the Restart button unlocks (up to 5 minutes), then restart.":
        "Fertig. Der NVIDIA-Treiber wird noch für deinen Kernel gebaut – warte, bis der Neustart-Knopf frei wird (bis zu 5 Minuten), dann neu starten.",
    "Setup is running. Please wait until it has finished – stopping dnf halfway can damage the system.":
        "Die Einrichtung läuft. Bitte warte, bis sie fertig ist – dnf mittendrin abzubrechen kann das System beschädigen.",
    "pkexec is missing (package polkit), so nothing can be set up from here.":
        "pkexec fehlt (Paket polkit), daher lässt sich hier nichts einrichten.",
    # groups
    "Basics": "Grundlagen",
    "Graphics": "Grafik",
    "If needed": "Bei Bedarf",
    "RTX 20xx, GTX 16xx and newer": "RTX 20xx, GTX 16xx und neuer",
    "GTX 9xx / 10xx, MX (580xx)": "GTX 9xx / 10xx, MX (580xx)",
    "GeForce 600 / 700 (470xx)": "GeForce 600 / 700 (470xx)",
    # steps
    "Update the system": "System aktualisieren",
    "dnf upgrade --refresh – everything else builds on an up-to-date system.":
        "dnf upgrade --refresh – alles Weitere baut auf einem aktuellen System auf.",
    "Update firmware": "Firmware aktualisieren",
    "BIOS/UEFI, SSD, Thunderbolt and more via fwupd, as far as the vendor takes part.":
        "BIOS/UEFI, SSD, Thunderbolt und mehr über fwupd – soweit der Hersteller mitmacht.",
    "Enable RPM Fusion": "RPM Fusion einschalten",
    "The source for codecs and proprietary drivers (free + nonfree).":
        "Die Quelle für Codecs und proprietäre Treiber (free + nonfree).",
    "Full multimedia codecs": "Vollständige Multimedia-Codecs",
    "Swap ffmpeg-free for the full FFmpeg and add the GStreamer plugins: H.264, H.265, AAC in Firefox, VLC, Kdenlive.":
        "ffmpeg-free gegen das vollständige FFmpeg tauschen und die GStreamer-Plugins nachziehen: H.264, H.265, AAC in Firefox, VLC, Kdenlive.",
    "Intel video acceleration": "Intel-Video-Beschleunigung",
    "intel-media-driver: hardware video decoding for Intel graphics from about 2014 on.":
        "intel-media-driver: Video-Dekodierung in Hardware für Intel-Grafik ab etwa 2014.",
    "AMD video acceleration": "AMD-Video-Beschleunigung",
    "The freeworld Mesa drivers with H.264/H.265 decoding and encoding.":
        "Die freeworld-Mesa-Treiber mit H.264/H.265 beim Dekodieren und Kodieren.",
    "NVIDIA driver": "NVIDIA-Treiber",
    "{gpu}. Proprietary driver with video acceleration; the kernel module is built in the background afterwards (up to 5 minutes) – do not restart before it is done.":
        "{gpu}. Proprietärer Treiber mit Video-Beschleunigung; das Kernelmodul wird danach im Hintergrund gebaut (bis zu 5 Minuten) – vorher nicht neu starten.",
    "Secure Boot is on: the driver module has to be signed, otherwise the screen stays black.":
        "Secure Boot ist an: Das Treibermodul muss signiert werden, sonst bleibt der Bildschirm schwarz.",
    "Flathub without filter": "Flathub ohne Filter",
    "Fedora ships Flathub with a filter that only shows a selection. This shows all apps.":
        "Fedora bringt Flathub mit einem Filter mit, der nur eine Auswahl zeigt. Danach sind alle Apps zu sehen.",
    "Remove the duplicate Flathub": "Doppeltes Flathub entfernen",
    "Flathub is set up twice (system and user), so Discover shows every app twice.":
        "Flathub ist doppelt eingerichtet (System und Benutzer), daher zeigt Discover jede App zweimal.",
    "{n} app(s) are installed from the user Flathub – reinstall them system-wide first.":
        "{n} App(s) sind aus dem Benutzer-Flathub installiert – erst systemweit neu installieren.",
    "Fonts for Word documents": "Schriften für Word-Dokumente",
    "Free fonts with the exact sizes of Arial, Times New Roman, Courier, Calibri and Cambria, so Word documents keep their layout.":
        "Freie Schriften mit exakt den Maßen von Arial, Times New Roman, Courier, Calibri und Cambria, damit Word-Dokumente ihren Umbruch behalten.",
    "OBS Studio as RPM": "OBS Studio als RPM",
    "With NVIDIA the RPM gets NVENC without extra packages (the Flatpak does not).":
        "Bei NVIDIA bekommt das RPM NVENC ohne Zusatzpakete (das Flatpak nicht).",
    "Play DVDs": "DVDs abspielen",
    "libdvdcss from RPM Fusion tainted. Judge the legal situation in your country yourself.":
        "libdvdcss aus RPM Fusion tainted. Die Rechtslage im eigenen Land selbst beurteilen.",
    "Older AppImages": "Ältere AppImages",
    "fuse + fuse-libs for AppImages that stop with a libfuse.so.2 error.":
        "fuse + fuse-libs für AppImages, die mit einem libfuse.so.2-Fehler abbrechen.",
}


def _pick() -> str:
    forced = os.environ.get("DNFSETUP_LANG", "").lower()
    if forced in ("de", "en"):
        return forced
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(var)
        if val:
            return "de" if val.lower().startswith("de") else "en"
    lang = (locale.getlocale()[0] or "").lower()
    return "de" if lang.startswith("de") else "en"


LANG = _pick()


def tr(text: str, **kw) -> str:
    out = DE.get(text, text) if LANG == "de" else text
    return out.format(**kw) if kw else out
