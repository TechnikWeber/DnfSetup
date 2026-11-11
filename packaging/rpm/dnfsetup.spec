Name:           dnfsetup
Version:        0.1.0
Release:        1%{?dist}
Summary:        Set up Fedora after installation: firmware, RPM Fusion, codecs, drivers
License:        MIT
URL:            https://github.com/TechnikWeber/DnfSetup
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
Requires:       python3-pyside6
Requires:       polkit
Requires:       dnf5
Recommends:     flatpak
Recommends:     fwupd
Recommends:     pciutils

%description
The usual post-install checklist for Fedora as one window: firmware, RPM
Fusion, multimedia codecs, video acceleration, the NVIDIA driver for your
card, Flathub without filter and a few extras. Shows what is already done and
runs the rest with one password prompt.

%prep
%autosetup

%build
# pure Python, nothing to build

%install
install -d %{buildroot}%{python3_sitelib}/dnfsetup
install -m644 dnfsetup/*.py dnfsetup/helper.sh dnfsetup/dnfsetup.svg \
    %{buildroot}%{python3_sitelib}/dnfsetup/
install -Dm755 /dev/stdin %{buildroot}%{_bindir}/dnfsetup <<'SH'
#!/usr/bin/python3 -s
from dnfsetup.app import main
raise SystemExit(main())
SH
desktop-file-install --dir=%{buildroot}%{_datadir}/applications share/dnfsetup.desktop
install -Dm644 dnfsetup/dnfsetup.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/dnfsetup.svg
install -Dm644 share/io.github.technikweber.dnfsetup.metainfo.xml \
    %{buildroot}%{_metainfodir}/io.github.technikweber.dnfsetup.metainfo.xml

%check
%{python3} -m unittest discover -s tests -t .

%files
%license LICENSE
%doc README.md CHANGELOG.md
%{_bindir}/dnfsetup
%{python3_sitelib}/dnfsetup/
%{_datadir}/applications/dnfsetup.desktop
%{_datadir}/icons/hicolor/scalable/apps/dnfsetup.svg
%{_metainfodir}/io.github.technikweber.dnfsetup.metainfo.xml

%changelog
* Wed Nov 11 2026 Philipp Weber - 0.1.0-1
- First release
