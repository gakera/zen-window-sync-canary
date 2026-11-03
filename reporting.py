import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse

from probe import request_json, release_asset


RUNTIME_FILES = ("probe.py", "sync_test.py", "window_setup.py", "fixture.html", "open-window.ps1", "capture-desktop.ps1")
ROOT = Path(__file__).parent
MARKER = re.compile(r"<!-- canary-result-v1\n(.*?)\n-->", re.DOTALL)
ICONS = {"PASS": "🟢", "FAIL": "🔴", "UNVERIFIED": "🟡"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def repository():
    return os.getenv("GITHUB_REPOSITORY", "gakera/zen-window-sync-canary")


def api(path, payload=None, method=None):
    return request_json("https://api.github.com/repos/" + repository() + path, payload, method)


def suite_id(revision=None):
    digest = hashlib.sha256(b"windows-2025/python-3.11/v1\n")
    for name in RUNTIME_FILES:
        content = subprocess.check_output(["git", "show", revision + ":" + name], cwd=ROOT).decode() if revision else (ROOT / name).read_text()
        digest.update((name + "\0" + content.replace("\r\n", "\n") + "\0").encode())
    return digest.hexdigest()


def descriptor(release):
    asset = release_asset(release, "zen.installer.exe")
    return {"tag": release["tag_name"], "id": release["id"], "asset_id": asset["id"], "asset": asset["name"], "digest": asset["digest"]}


def get_release(tag="latest"):
    suffix = "latest" if tag == "latest" else "tags/" + urllib.parse.quote(tag, safe="")
    return descriptor(request_json("https://api.github.com/repos/zen-browser/desktop/releases/" + suffix))


def matching(results, release, fingerprint):
    return sorted([result for result in results if result.get("release") == release and result.get("suite_id") == fingerprint], key=lambda result: (result["tested_at"], result["run_id"], result["run_attempt"]))


def should_test(results, release, fingerprint, force=False):
    previous = matching(results, release, fingerprint)
    if force or not previous:
        return True
    if previous[-1]["classification"] in ("PASS", "FAIL"):
        return False
    return len(previous) < 3


def read_results():
    results = []
    trusted = {repository().split("/")[0], "github-actions[bot]"}
    page = 1
    while True:
        comments = api(f"/issues/{os.environ['STATUS_ISSUE']}/comments?per_page=100&page={page}")
        for comment in comments:
            if comment["user"]["login"] not in trusted:
                continue
            marker = MARKER.search(comment.get("body", ""))
            if not marker:
                continue
            try:
                result = json.loads(marker.group(1))
                if result["classification"] not in ICONS:
                    continue
                if not all(key in result for key in ("release", "suite_id", "tested_at", "run_id", "run_attempt")):
                    continue
                result["comment_id"] = comment["id"]
                results.append(result)
            except (ValueError, KeyError, TypeError):
                continue
        if len(comments) < 100:
            return results
        page += 1


def run_url(result):
    return f"https://github.com/{repository()}/actions/runs/{int(result['run_id'])}"


def cell(value):
    return str(value).replace("\n", " ").replace("|", "\\|").replace("`", "'").replace("<", "&lt;")


def concise_reason(report):
    target = report.get("sync-target-state", {})
    if report.get("classification") == "FAIL" and target.get("url") == "about:blank":
        return "The matching synchronized tab in B remained empty about:blank."
    if report.get("classification") == "PASS":
        return "Live state survived A → B → A; a trusted click in B reached the fixture server."
    return str(report.get("reason", "No complete browser evidence"))[:220]


def make_result(report, release, fingerprint, run_id, attempt=1, job_result=None):
    classification = report.get("classification", "UNVERIFIED")
    reason = concise_reason(report)
    if classification not in ICONS:
        classification = "UNVERIFIED"
    if report.get("release") != release:
        classification, reason = "UNVERIFIED", "Missing report or release/asset identity changed after discovery."
    elif not report.get("p0_complete"):
        classification = "UNVERIFIED"
    elif classification == "PASS" and not report.get("sync_scenario_complete"):
        classification, reason = "UNVERIFIED", "Required scenario did not complete."
    if job_result and job_result != "success" and classification == "PASS":
        classification, reason = "UNVERIFIED", "Browser job did not complete successfully."
    return {"release": release, "suite_id": fingerprint, "suite_revision": report.get("suite_revision", os.getenv("GITHUB_SHA", "unknown")), "classification": classification, "reason": reason, "tested_at": now(), "run_id": int(run_id), "run_attempt": int(attempt)}


def comment_body(result):
    public_result = {key: value for key, value in result.items() if key != "comment_id"}
    return (f"### {ICONS[result['classification']]} {result['classification']} — Zen {cell(result['release']['tag'])}\n\n"
            f"{cell(result['reason'])}\n\n[Run, logs and screenshot artifacts]({run_url(result)}) · "
            f"Test suite `{result['suite_id'][:12]}` · {result['tested_at']}\n\n"
            "Screenshot artifacts expire after 7 days; this compact result remains in the issue history.\n\n"
            "<!-- canary-result-v1\n" + json.dumps(public_result, sort_keys=True) + "\n-->")


def dashboard(release, results, fingerprint, checked_at, error=None):
    current = matching(results, release, fingerprint) if release else []
    verdict = current[-1]["classification"] if current else "UNVERIFIED"
    heading = f"{ICONS[verdict]} **Latest stable: Zen {cell(release['tag'])} — {verdict}**" if release else "🟡 **UNVERIFIED — latest release lookup failed**"
    lines = ["# Zen Windows synchronized-tab canary", "", heading, "",
             "Scope: one tab opened from a link in A, selected by its shared tab ID in B, with live state and a fresh click checked. This is not a general security or update-safety certification.", "",
             f"Last release lookup: **{checked_at} UTC** · Current test suite: `{fingerprint[:12]}`", "",
             "If this timestamp is over 48 hours old, treat monitoring as stale and check Actions. GitHub may delay schedules or disable them after 60 days without repository activity.", ""]
    if error:
        lines.extend(["**Monitor error:** " + cell(error), ""])
    if release and not current:
        lines.extend(["No completed result matches this release asset and current test suite yet.", ""])
    if current:
        lines.extend([cell(current[-1]["reason"]), "", f"[Latest stable evidence]({run_url(current[-1])})", ""])
    latest_by_tag = {}
    for result in sorted(results, key=lambda entry: entry["tested_at"]):
        latest_by_tag[result["release"]["tag"]] = result
    lines.extend(["## Release results", "", "| Zen release | Result | Test suite | Tested (UTC) | Evidence |", "| --- | --- | --- | --- | --- |"])
    for result in sorted(latest_by_tag.values(), key=lambda entry: entry["tested_at"], reverse=True)[:20]:
        label = "current" if result["suite_id"] == fingerprint else "older suite"
        lines.append(f"| {cell(result['release']['tag'])} | {ICONS[result['classification']]} **{result['classification']}** | `{result['suite_id'][:12]}` ({label}) | {result['tested_at']} | [Logs / screenshots]({run_url(result)}) |")
    lines.extend(["", "## Controls", "",
                  f"[Run or retest a release](https://github.com/{repository()}/actions/workflows/feasibility.yml) · [All runs](https://github.com/{repository()}/actions)", "",
                  "Automatic lookup: daily at 06:17 UTC. Windows runs only for a new release/asset/test-suite identity. UNVERIFIED identities get at most three automatic attempts; use a manual forced retest after that. FAIL assertions are never retried within a test run.", "",
                  "PASS = all required assertions ran. FAIL = behavioral mismatch. UNVERIFIED = setup, automation or evidence could not establish a verdict. A historical PASS never changes the latest-stable headline.", "",
                  "Subscribe to this issue for actual test-result comments. Unchanged daily checks update this summary without adding comments. Screenshots expire after 7 days; compact result artifacts after 90 days; result comments remain until removed."])
    return "\n".join(lines)


def summary(text):
    print(text)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as output:
            output.write(text + "\n")


def discover():
    release = get_release(os.getenv("REQUESTED_RELEASE", "latest"))
    fingerprint = suite_id()
    run = should_test(read_results(), release, fingerprint, os.getenv("FORCE_RETEST", "false").lower() == "true")
    values = {"should_run": str(run).lower(), "release": release["tag"], "release_json": json.dumps(release, separators=(",", ":")), "suite_id": fingerprint}
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        for key, value in values.items():
            output.write(key + "=" + value + "\n")
    summary(f"## Release discovery\n\nZen **{cell(release['tag'])}** · Windows test required: **{run}**\n\n[Live status issue](https://github.com/{repository()}/issues/{os.environ['STATUS_ISSUE']})\n\nA skipped Windows job keeps the previously recorded release verdict; it does not certify the release as passing.")


def record():
    try:
        report = json.loads(Path("evidence/report.json").read_text())
    except (OSError, ValueError):
        report = {}
    result = make_result(report, json.loads(os.environ["SELECTED_RELEASE"]), os.environ["SELECTED_SUITE"], os.environ["GITHUB_RUN_ID"], os.getenv("GITHUB_RUN_ATTEMPT", "1"), os.getenv("PROBE_RESULT"))
    payload = {"body": comment_body(result)}
    existing = next((entry for entry in read_results() if entry["run_id"] == result["run_id"] and entry["run_attempt"] == result["run_attempt"]), None)
    if existing:
        api("/issues/comments/" + str(existing["comment_id"]), payload, "PATCH")
    else:
        api(f"/issues/{os.environ['STATUS_ISSUE']}/comments", payload)
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/result.json").write_text(json.dumps(result, indent=2))
    summary(comment_body(result).split("<!--")[0])
    return {"PASS": 0, "FAIL": 1, "UNVERIFIED": 2}[result["classification"]]


def refresh():
    results = read_results()
    error = None
    try:
        release = get_release()
    except Exception as exception:
        release, error = None, str(exception)[:300]
    body = dashboard(release, results, suite_id(), now(), error)
    api(f"/issues/{os.environ['STATUS_ISSUE']}", {"body": body}, "PATCH")
    summary(body)
    return 2 if error else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("discover", "record", "refresh", "seed"))
    parser.add_argument("--report")
    parser.add_argument("--run-id")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "seed":
        report = json.loads(Path(args.report).read_text())
        fingerprint = suite_id(report["suite_revision"])
        if fingerprint != suite_id():
            raise ValueError("Historical report used different runtime files; cannot seed as the current suite")
        result = make_result(report, report["release"], fingerprint, args.run_id)
        result["tested_at"] = report["timestamp"]
        Path(args.output).write_text(json.dumps({"body": comment_body(result)}))
        return 0
    return {"discover": discover, "record": record, "refresh": refresh}[args.command]() or 0


if __name__ == "__main__":
    raise SystemExit(main())
