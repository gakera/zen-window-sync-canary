import unittest
from probe import release_asset


class ReleaseSelectionTests(unittest.TestCase):
    def test_selects_installer_instead_of_update_archive(self):
        installer = {"name": "zen.installer.exe", "digest": "sha256:" + "a" * 64}
        release = {"assets": [{"name": "windows.mar"}, installer]}
        self.assertEqual(release_asset(release, "zen.installer.exe"), installer)

    def test_rejects_unverifiable_or_unstable_release(self):
        for release in [
            {"prerelease": True, "assets": []},
            {"draft": True, "assets": []},
            {"assets": [{"name": "zen.installer.exe"}]},
            {"assets": []},
        ]:
            with self.subTest(release=release), self.assertRaises(ValueError):
                release_asset(release, "zen.installer.exe")


if __name__ == "__main__":
    unittest.main()
