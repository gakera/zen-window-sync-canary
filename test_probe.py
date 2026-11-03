import unittest
import io
from unittest.mock import patch
from probe import release_asset, request_json


class ReleaseSelectionTests(unittest.TestCase):
    def test_token_is_only_sent_to_github_api(self):
        for url, expected in [("https://api.github.com/repos/test/test", True), ("http://127.0.0.1:4444/status", False)]:
            with self.subTest(url=url), patch.dict("os.environ", {"GITHUB_TOKEN": "test-placeholder"}), patch("urllib.request.urlopen", return_value=io.StringIO('{}')) as opener:
                request_json(url)
                self.assertEqual(opener.call_args.args[0].has_header("Authorization"), expected)

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
