# Maintainer guide

## Local checks

Run `python3 -m unittest -v` from the repository root. Local tests use Python's standard library and do not launch a browser or download releases. Windows browser testing runs through [GitHub Actions](https://github.com/gakera/zen-window-sync-canary/actions/workflows/feasibility.yml); a Windows VM or Firefox development build is not required on the maintainer's machine.

## Components

- `probe.py`: release download and SHA-256 verification, disposable profile, fixture server, browser startup, evidence and classification.
- `window_setup.py` / `open-window.ps1`: native second-window creation with bounded retries and duplicate-window guards.
- `sync_test.py`: link-based tab creation, shared-ID selection through real browser UI input, live-state assertions and optional post-verdict presentation captures.
- `fixture.html`: local counter, scroll, history and page ID; trusted click events are reported to the fixture server.
- `capture-desktop.ps1`: full Windows runner desktop capture.
- `reporting.py`: release discovery, deduplication, durable result comments and the pinned status dashboard.

Browser-UI mode uses geckodriver's `--allow-system-access` flag only in the disposable Windows runner. No script repairs Zen's synchronization state. Tests use released binaries, independently of upstream Mochitest helpers. Upstream Zen remains read-only.

## Scheduling and retesting

The workflow checks the upstream stable release daily at 06:17 UTC. GitHub release events apply to the repository containing the workflow, so upstream releases are discovered through the release API.

The test identity includes the release and asset IDs, asset digest and runtime-file fingerprint. Unchanged PASS/FAIL identities skip Windows. UNVERIFIED identities get at most three automatic attempts. Manual runs accept a stable tag or `latest`; the Retest input defaults to true and bypasses deduplication. Only main-branch runs update the dashboard.

Source-file fingerprinting allows documentation-only changes without forcing another Windows run. Imported historical controls must match the runtime files at their recorded test revision. Reporting and test changes still need their appropriate local validation.

## Reporting

[Issue #1](https://github.com/gakera/zen-window-sync-canary/issues/1) holds the latest-stable headline and version table. Its title also includes the latest verdict. Actual test runs add machine-readable result comments; unchanged checks refresh the summary without adding comments. Only comments authored by the repository owner or GitHub Actions bot are treated as result records.

The issue-body renderer is serialized and rebuilds from durable comments, so parallel test jobs do not overwrite each other's history. Historical PASS results never determine the latest-stable headline. A successful lightweight discovery workflow does not mean the browser passed.

Result publication deliberately exits nonzero after saving FAIL/UNVERIFIED results. This enforces the verdict in Actions as well as on the dashboard; it does not by itself indicate that publication failed.

## Evidence

- Browser traces, page screenshots and full desktop captures: Actions artifacts, retained for 7 days.
- Compact authoritative result: `release-result-*` artifact, retained for 90 days.
- Release verdict history: result comments, retained until removed.

Files prefixed `desktop-` show the full runner desktop; other PNGs show only the page viewport. Post-verdict clean captures close unrelated setup tabs using normal UI input and are saved only if the expected passing state or observed blank failure remains. Cleanup errors do not overwrite the already recorded regression verdict; original captures are retained.

Before publishing screenshots in documentation, inspect them for clarity and privacy and obtain the owner's approval. Preserve original image bytes and record their source run. Committed documentation images remain available after Actions artifacts expire.

## Troubleshooting

- **UNVERIFIED during startup:** inspect `window_setup_attempts`, driver logs and desktop screenshots. Window creation allows three attempts, observing both native windows and browser-UI handles; late, partial or extra windows prevent duplicate shortcuts. Regression assertions are never retried to turn a failure green.
- **Scroll mismatch:** expected state must be sampled only after scrolling settles. The first historical control exposed sampling during smooth scrolling; this was a harness issue, not evidence of a browser regression.
- **Blank content:** confirm the selected shared tab ID, source deselection, content binding and recorded document state. A sidebar label alone is insufficient evidence.
- **Stale dashboard:** a lookup older than 48 hours needs investigation. GitHub can delay schedules or disable public scheduled workflows after 60 days without repository activity; re-enable the workflow if needed.
- **Missing artifacts or changed release identity:** keep the authoritative result UNVERIFIED.

See [development history](development-history.md) for the initial WebDriver limitations, onboarding issues and earlier comparison runs. Those notes describe historical stages, not the current checklist.
