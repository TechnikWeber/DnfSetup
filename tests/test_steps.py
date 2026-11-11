import unittest

from dnfsetup import steps as s


class Lspci(unittest.TestCase):
    def test_vendors(self):
        text = (
            "00:02.0 VGA compatible controller [0300]: Intel Corporation Kaby Lake-R GT2 [UHD Graphics 620] [8086:5917] (rev 07)\n"
            "01:00.0 3D controller [0302]: NVIDIA Corporation GP108M [GeForce MX150] [10de:1d10] (rev a1)\n"
            "03:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Navi 23 [Radeon RX 6600] [1002:73ff] (rev c7)\n"
            "00:1f.3 Audio device [0403]: Intel Corporation Sunrise Point-LP HD Audio [8086:9d71] (rev 21)\n"
        )
        gpus = s.parse_lspci(text)
        self.assertEqual([g.vendor for g in gpus], ["intel", "nvidia", "amd"])
        self.assertEqual(gpus[1].name, "NVIDIA Corporation GP108M [GeForce MX150]")


class NvidiaSeries(unittest.TestCase):
    def test_branches(self):
        cases = {
            "NVIDIA Corporation AD104 [GeForce RTX 4070]": "current",
            "NVIDIA Corporation TU117 [GeForce GTX 1650]": "current",
            "NVIDIA Corporation GA102GL [RTX A5000]": "current",
            "NVIDIA Corporation GP106 [GeForce GTX 1060 6GB]": "580xx",
            "NVIDIA Corporation GM204 [GeForce GTX 970]": "580xx",
            "NVIDIA Corporation GP108M [GeForce MX150]": "580xx",
            "NVIDIA Corporation GP107GL [Quadro P620]": "580xx",
            "NVIDIA Corporation GK104 [GeForce GTX 770]": "470xx",
            "NVIDIA Corporation GK208B [GeForce GT 710]": "470xx",
            "NVIDIA Corporation GK107GL [Quadro K600]": "470xx",
            "NVIDIA Corporation GT218 [GeForce 210]": "",
        }
        for name, want in cases.items():
            self.assertEqual(s.nvidia_series(name), want, name)


class Flatpak(unittest.TestCase):
    def test_duplicate_user_remote(self):
        text = "fedora\tsystem,oci\t-\nflathub\tsystem\t-\nflathub\tuser\t-\n"
        self.assertEqual(s.parse_flatpak_remotes(text), ("ok", True))

    def test_filtered_and_disabled(self):
        self.assertEqual(s.parse_flatpak_remotes("flathub\tsystem\t/usr/share/flatpak/fedora-flathub.filter\n"),
                         ("filtered", False))
        self.assertEqual(s.parse_flatpak_remotes("flathub\tsystem,disabled\t-\n"), ("disabled", False))
        self.assertEqual(s.parse_flatpak_remotes(""), ("", False))


class Rpm(unittest.TestCase):
    def test_installed(self):
        text = "ffmpeg\npackage obs-studio is not installed\nfuse\n"
        self.assertEqual(s.parse_rpm_installed(text), {"ffmpeg", "fuse"})


class Steps(unittest.TestCase):
    def fresh(self, **kw):
        f = s.Facts(release=45, have={"dnf", "rpm", "flatpak", "fwupdmgr"}, flathub_system="filtered",
                    updates=3, firmware_updates=0, **kw)
        return f

    def test_fresh_install(self):
        f = self.fresh(gpus=[s.Gpu("nvidia", "NVIDIA Corporation GP106 [GeForce GTX 1060 6GB]")])
        st = {x.id: x for x in s.build_steps(f)}
        self.assertEqual(st["upgrade"].state, s.TODO)
        self.assertEqual(st["firmware"].state, s.DONE)
        self.assertEqual(st["rpmfusion"].state, s.TODO)
        self.assertEqual(st["flathub"].state, s.TODO)
        self.assertEqual(st["nvidia"].action, "nvidia:580xx")
        self.assertTrue(st["nvidia"].default)
        self.assertNotIn("intel", st)

    def test_secure_boot_unticks_nvidia(self):
        f = self.fresh(gpus=[s.Gpu("nvidia", "X [GeForce RTX 3060]")], secure_boot=True)
        nv = next(x for x in s.build_steps(f) if x.id == "nvidia")
        self.assertFalse(nv.default)
        self.assertIn("Secure Boot", nv.note)

    def test_requirements_pulled_in(self):
        f = self.fresh(gpus=[s.Gpu("intel", "Intel UHD")])
        steps = s.build_steps(f)
        root, user = s.order_actions(steps, {"codecs", "intel"})
        self.assertEqual(root, ["rpmfusion", "codecs", "intel"])
        self.assertEqual(user, [])

    def test_done_requirement_not_repeated(self):
        f = self.fresh(installed={"rpmfusion-free-release", "rpmfusion-nonfree-release", "rpmfusion-free-appstream-data"})
        root, _ = s.order_actions(s.build_steps(f), {"dvd"})
        self.assertEqual(root, ["dvd"])

    def test_rpmfusion_without_appstream_data_is_open(self):
        # release packages alone (the old "dnf upgrade @core" route on dnf5) leave Discover blind
        f = self.fresh(installed={"rpmfusion-free-release", "rpmfusion-nonfree-release"})
        st = next(x for x in s.build_steps(f) if x.id == "rpmfusion")
        self.assertEqual(st.state, s.TODO)

    def test_every_action_known_to_helper(self):
        from importlib import resources
        helper = resources.files("dnfsetup").joinpath("helper.sh").read_text()
        f = self.fresh(gpus=[s.Gpu("intel", "i"), s.Gpu("amd", "a"), s.Gpu("nvidia", "[GeForce RTX 4070]")])
        for st in s.build_steps(f):
            if st.root:
                pattern = st.action.split(":")[0] + (":*)" if ":" in st.action else ")")
                self.assertIn(pattern, helper, st.id)

    def test_check_counts(self):
        self.assertEqual(s.count_check_upgrade(0, ""), 0)
        self.assertEqual(s.count_check_upgrade(100, "Upgrades\ngit.x86_64  2.56.0-1.fc45  updates\n"), 1)
        self.assertIsNone(s.count_check_upgrade(1, "error"))
        self.assertEqual(s.count_fwupd('{"Devices": [{"Name": "x"}]}'), 1)
        self.assertIsNone(s.count_fwupd("garbage"))


if __name__ == "__main__":
    unittest.main()
