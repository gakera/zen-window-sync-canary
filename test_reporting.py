import json
import os
import unittest
from unittest.mock import patch

from reporting import comment_body, dashboard, make_result, read_results, record, should_test


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.release = {"tag": "1.24b", "id": 24, "asset_id": 240, "asset": "zen.installer.exe", "digest": "sha256:abc"}
        self.report = {"classification": "PASS", "release": self.release, "p0_complete": True, "sync_scenario_complete": True, "suite_revision": "revision"}
        self.result = make_result(self.report, self.release, "suite-current", 123)

    def test_known_pass_and_fail_do_not_consume_daily_windows_runner(self):
        for classification in ("PASS", "FAIL"):
            with self.subTest(classification=classification):
                result = dict(self.result, classification=classification)
                self.assertFalse(should_test([result], self.release, "suite-current"))
                self.assertTrue(should_test([result], self.release, "suite-current", force=True))

    def test_new_asset_or_suite_requires_testing(self):
        self.assertTrue(should_test([self.result], dict(self.release, digest="sha256:changed"), "suite-current"))
        self.assertTrue(should_test([self.result], self.release, "suite-new"))

    def test_unverified_automatic_attempts_are_bounded(self):
        result = dict(self.result, classification="UNVERIFIED")
        self.assertTrue(should_test([result] * 2, self.release, "suite-current"))
        self.assertFalse(should_test([result] * 3, self.release, "suite-current"))

    def test_historical_pass_does_not_make_latest_stable_green(self):
        current = dict(self.result, classification="FAIL")
        historical = dict(self.result, release=dict(self.release, tag="1.21.8b", id=21), tested_at="9999-01-01")
        body = dashboard(self.release, [current, historical], "suite-current", "today")
        self.assertIn("Latest stable: Zen 1.24b — FAIL", body)
        self.assertIn("1.21.8b", body)

    def test_new_suite_cannot_reuse_old_pass_headline(self):
        body = dashboard(self.release, [self.result], "suite-new", "today")
        self.assertIn("Latest stable: Zen 1.24b — UNVERIFIED", body)
        self.assertIn("older suite", body)

    def test_discovery_error_has_no_green_headline(self):
        body = dashboard(None, [self.result], "suite-current", "today", "Network failed")
        self.assertIn("UNVERIFIED — latest release lookup failed", body)

    def test_missing_incomplete_or_mismatched_report_is_unverified(self):
        reports = [{}, dict(self.report, p0_complete=False), dict(self.report, sync_scenario_complete=False), dict(self.report, release=dict(self.release, digest="changed"))]
        for report in reports:
            with self.subTest(report=report):
                self.assertEqual(make_result(report, self.release, "suite", 123)["classification"], "UNVERIFIED")
        self.assertEqual(make_result(self.report, self.release, "suite", 123, job_result="failure")["classification"], "UNVERIFIED")

    def test_untrusted_comment_cannot_forge_a_passing_result(self):
        body = comment_body(self.result)
        comments = [{"id": 1, "user": {"login": "someone-else"}, "body": body}, {"id": 2, "user": {"login": "github-actions[bot]"}, "body": body}]
        with patch.dict(os.environ, {"STATUS_ISSUE": "1", "GITHUB_REPOSITORY": "gakera/zen-window-sync-canary"}), patch("reporting.api", return_value=comments):
            self.assertEqual([result["comment_id"] for result in read_results()], [2])

    def test_report_retry_updates_existing_run_comment(self):
        environment = {"STATUS_ISSUE": "1", "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1", "SELECTED_RELEASE": json.dumps(self.release), "SELECTED_SUITE": "suite-current", "PROBE_RESULT": "success"}
        existing = dict(self.result, comment_id=55)
        with patch.dict(os.environ, environment), patch("reporting.Path.read_text", return_value=json.dumps(self.report)), patch("reporting.Path.mkdir"), patch("reporting.Path.write_text"), patch("reporting.summary"), patch("reporting.read_results", return_value=[existing]), patch("reporting.api") as api:
            self.assertEqual(record(), 0)
            self.assertEqual(api.call_args.args[0], "/issues/comments/55")
            self.assertEqual(api.call_args.args[2], "PATCH")


if __name__ == "__main__":
    unittest.main()
