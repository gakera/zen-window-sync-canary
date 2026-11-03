import unittest
import io
from unittest.mock import patch
from probe import release_asset, request_json
from sync_test import state_differences


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


class LiveStateTests(unittest.TestCase):
    def setUp(self):
        self.state = {"token": "document-a", "counter": 1, "url": "http://127.0.0.1:1234/sync-fixture?state=1", "scroll": 700, "visibility": "visible", "width": 900, "height": 600}

    def test_preserved_state_passes(self):
        self.assertEqual(state_differences(self.state, dict(self.state)), [])

    def test_reloaded_document_fails_even_if_other_state_restored(self):
        self.assertTrue(any("token" in difference for difference in state_differences(self.state, dict(self.state, token="document-b"))))

    def test_blank_new_tab_fails(self):
        self.assertTrue(state_differences(self.state, {"url": "about:blank"}))

    def test_each_live_state_loss_is_detected(self):
        for change in [{"counter": 0}, {"scroll": 0}, {"url": "http://127.0.0.1:1234/sync-fixture"}, {"visibility": "hidden"}, {"width": 0}]:
            with self.subTest(change=change):
                self.assertTrue(state_differences(self.state, dict(self.state, **change)))


if __name__ == "__main__":
    unittest.main()
