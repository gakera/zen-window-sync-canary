# Development history (archived)

These are the original investigation notes, retained as historical context. Some sections describe intermediate assumptions or work that has since been completed. See the [README](../README.md) for the public overview and the [maintainer guide](maintenance.md) for current operation.

## Live status

**[Open the pinned release-status dashboard](https://github.com/gakera/zen-window-sync-canary/issues/1)** · [Run / retest a release](https://github.com/gakera/zen-window-sync-canary/actions/workflows/feasibility.yml)

The dashboard headline tracks the latest published stable Zen release, independently of historical/manual test runs. Daily release discovery is scheduled for **00:00 UTC** on Ubuntu; Windows runs only for a new release ID, asset ID/digest or runtime test-suite fingerprint. An unchanged FAIL remains a FAIL on the dashboard even if the lightweight daily workflow is green. No workflow badge is used as a release-safety signal.

Manual runs accept an exact release tag or `latest`. **Retest** defaults to true; turn it off to exercise the automatic discovery/deduplication path. UNVERIFIED identities get at most three automatic attempts, then require a manual forced retest. Results from setup failures or missing artifacts remain UNVERIFIED. Only main-branch runs can update the status issue.

Actual tests add durable result comments to the status issue; unchanged daily checks only refresh the summary. Subscribe to that issue for result notifications. The body renderer is serialized, while test jobs run independently; it rebuilds from durable comments so parallel tests do not lose history. A source-file fingerprint prevents documentation/reporting-only edits from forcing another Windows run. Seeded controls are checked against the actual recorded test revision's runtime files before import.

Evidence: screenshots and browser logs expire after 7 days, compact machine-readable result artifacts after 90 days, and result comments remain until removed. The dashboard shows the last successful lookup time; if older than 48 hours, treat it as stale. GitHub can delay schedules and disables public scheduled workflows after 60 days without repository activity. Check Actions and re-enable the workflow if necessary.

Native GitHub options used here: Actions summaries for each check, artifacts for screenshots/logs, and a pinned issue for the durable three-state status. GitHub also offers workflow badges and Pages; a single latest-run badge would conflate historical control runs with the latest release verdict. Pages can be added later if a separate visual site is useful.

End-to-end reporting validation: [unchanged discovery skipped Windows](https://github.com/gakera/zen-window-sync-canary/actions/runs/41710318029), [1.21.8b PASS was published](https://github.com/gakera/zen-window-sync-canary/actions/runs/41710323529), and [1.24b FAIL was published](https://github.com/gakera/zen-window-sync-canary/actions/runs/41710328475). Both result comments survived parallel execution and the latest-stable headline stayed FAIL. The pinned issue title also carries the current verdict. The result-publication step deliberately exits nonzero for FAIL/UNVERIFIED after saving the result; this keeps those tests from appearing green.

## Verified release comparison

Both runs below used the same hardened test revision (ecfa7ab) and released Windows x64 binaries on GitHub-hosted Windows runners:

| Release | Focused live-state result | Evidence |
| --- | --- | --- |
| 1.21.8b | PASS: same document token, counter, history and settled scroll in B; trusted click in B; updated state back in A | [Run 41707940717](https://github.com/gakera/zen-window-sync-canary/actions/runs/41707940717) |
| 1.24b | FAIL: selecting the matching shared tab in B leaves visible empty about:blank content | [Run 41707935387](https://github.com/gakera/zen-window-sync-canary/actions/runs/41707935387) |

This demonstrates a meaningful working/affected contrast for this scenario. It is not a blanket safety claim or proof of the exact first affected release. Native window creation has intermittently failed before the regression scenario; those runs stay UNVERIFIED, with bounded setup retries and separate attempt evidence added afterward.

Both hardened confirmation runs created two windows on attempt one; retry recovery has therefore been validated by deterministic local tests, not yet observed in a live recovery. Twelve local checks pass, including retry limits, late-window detection, partial-window guards and refusing a third window. Before retry hardening, the same contrast was also observed using revision 23a63ca in [1.21.8b](https://github.com/gakera/zen-window-sync-canary/actions/runs/41707427309) and [1.24b](https://github.com/gakera/zen-window-sync-canary/actions/runs/41707421534).

Initial reproduction: **FAIL on 1.24b** in [41706707017](https://github.com/gakera/zen-window-sync-canary/actions/runs/41706707017). A real link click created a fixture tab in A; after state mutations and selection of a distractor in A, the same shared tab ID selected in B displayed a visible, empty about:blank document. The source and destination WebDriver content handles were bound to that same Zen shared ID, and the selected ID was rechecked after binding. Full desktop screenshots show the blank selected tab and the source distractor. The hardened confirmation runs and working historical control are recorded above.

The [first historical 1.21.8b control](https://github.com/gakera/zen-window-sync-canary/actions/runs/41707012345) transferred the same live document, counter and history URL; its only mismatch was scroll (1086 sampled in A versus 1400 settled in B). This exposed source sampling during smooth scrolling, so the harness now requires a stable scroll position for 0.6 seconds before recording expected state. That initial control result must not be interpreted as a historical browser regression. The [1.24b repeat](https://github.com/gakera/zen-window-sync-canary/actions/runs/41707007668) was UNVERIFIED during window creation. The harness now waits for Zen startup/workspace initialization before attempting the second window.

## Focused synchronized-tab scenario

After P0, click a fixture link with target=_blank to open one normal tab in A. Read its shared Zen tab ID and inspect its counterpart in the other window using WebDriver browser-UI mode. Click the real sidebar tab through WebDriver's element-click endpoint; no script repairs or replaces Zen's synchronization logic. Browser-UI mode requires geckodriver's documented `--allow-system-access` flag, used only inside the disposable runner against the released binary. This is separate from in-tree Mochitest. A link is used because native/privileged address-bar typing proved unreliable on the runner; the destination window is never navigated independently.

Mutate the fixture in A with a real counter click, history button and wheel scroll. Select a normal distractor tab in A before selecting the same shared fixture tab in B. Assert visible content, document token, counter, history URL and scroll; click again in B and require a server-observed trusted event. Deselect in B and return to A, checking the updated live state again. Save tab inventories, selected IDs, state observations, page screenshots and full desktop screenshots. A blank New Tab in B must fail this test even if the sidebar label or remembered URL looks correct.

PASS means this one required scenario completed; broader release safety and historical regression sensitivity remain unproven. FAIL means a behavioral mismatch after identifiable UI selection, including an absent mirrored tab after bounded polling. UNVERIFIED means required automation/setup/evidence did not complete. Expected failure on 1.24b is not overridden to green. Each manually dispatched run has its own runner VM and can execute concurrently.

The user expects the synchronized-state regression to fail on 1.24b. Treat 1.24b as an expected failing candidate, pending reproduction. Keep normal regression semantics: a confirmed state-loss assertion is FAIL, not an expected-failure override that makes the run green. A WebDriver failure is UNVERIFIED and supplies no evidence about the sync regression.

## First milestone

The manually triggered workflow downloads a real stable Windows x64 Zen installer, verifies its published SHA-256, extracts it with the runner's 7-Zip, disables updates in the disposable extracted application, and attempts a headed geckodriver session with a fresh temporary profile. No Python packages are required. It checks a trusted page click, visible document, creation of two window handles, window switching, and a screenshot. Installer extraction, first-run setup, and WebDriver support remain experimental until a Windows run succeeds.

P0 success is automation evidence only; the subsequent synchronized-state scenario determines the scoped PASS/FAIL result. Errors identify their stage and retain trace logs. Runner timeout or setup failure may leave only partial evidence and must be treated as UNVERIFIED. Artifacts expire after seven days; inspect them before sharing. They contain only a disposable local fixture, but driver traces include profile paths.

## Run locally

Window-creation hardening: wait for Zen startup/workspace initialization, verify the foreground HWND, then allow at most three New Window attempts with a ten-second observation window each. Every attempt logs native windows, browser-UI windows and content handles and saves a desktop screenshot. Retry only when both window observers still report one window and no new tab handle; a late, partial or extra window blocks duplicate input. Setup retries never retry or overwrite a failed regression assertion.

Screenshot scope: `browser.png`, `failure.png`, `before-new-window.png`, and `second-window.png` are WebDriver page viewport captures and exclude browser chrome. Files prefixed `desktop-` capture the entire Windows runner's virtual desktop, including browser frames, sidebar tabs, and any overlap. They show only the disposable CI desktop, never the user's Mac. Desktop capture errors are recorded separately in report.json.

`python3 -m unittest -v` runs local harness, release-discovery and reporting checks on macOS without downloads or browser launch. `probe.py` runs only on Windows. It writes evidence/report.json and evidence/summary.md. Use workflow_dispatch with `latest` or an exact stable release tag. `reporting.py` handles discovery, deduplication, durable status comments and dashboard refresh through GitHub's API.

## Verified research, 2026-11-03

- Latest stable [1.24b](https://github.com/zen-browser/desktop/releases/tag/1.24b), release ID 428415009, has zen.installer.exe with SHA-256 2d55965f1952f2e5489dfaf954d613ebbf6361c5ca2bcad95ab8d3c0a481d6a4. windows.mar is an update payload. Discovery resolves latest dynamically and records identity and digest for each attempt.
- [Issue 16155](https://github.com/zen-browser/desktop/issues/16155) reports session initialization crashes, including fresh profiles. A handshake or running process alone is insufficient. Probe failures remain UNVERIFIED.
- [Upstream window_sync](https://github.com/zen-browser/desktop/tree/dev/src/zen/tests/window_sync) uses zen.window-sync.enabled=true and zen.urlbar.replace-newtab=false. Its head.js waits for workspace initialization and uses BrowserTestUtils and gZenWindowSync. Those privileged in-tree helpers cannot simply be run against release binaries. Upstream pr-test.yml bootstraps the engine and lints; this project does not reproduce that pipeline.
- [Standard public Windows runners](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job) are free; [private-repo usage](https://docs.github.com/en/billing/concepts/product-billing/github-actions) draws on plan allowances, then charges. Storage has separate limits. Public visibility needs the owner's approval. windows-2025 is Windows Server, so later Windows 11 reproduction may still be necessary.
- Action refs were resolved through GitHub's API: checkout v6, setup-python v6, upload-artifact v7. Driver v0.37.1 is explicitly selected and its release digest verified at runtime.

## Next gates

Native Ctrl+N in [41703349658](https://github.com/gakera/zen-window-sync-canary/actions/runs/41703349658) expanded WebDriver handles from two to four. WebDriver exposes tabs, so requiring exactly one new handle was an incorrect probe assumption. The next probe enumerates visible MozillaWindowClass windows owned by the disposable browser PID, requires a one-to-two native window transition, then finds a second-window tab by changing its window geometry and verifying the original window's geometry remains unchanged. This establishes separate windows even with multiple mirrored tab handles.

Third run [41702868321](https://github.com/gakera/zen-window-sync-canary/actions/runs/41702868321) found no new WebDriver handle after a WebDriver Ctrl+N action. The next attempt activates the disposable browser process and sends Ctrl+N through native Windows input using WScript.Shell, then independently polls WebDriver handles. A new handle alone still needs validation that it represents the intended separate synchronized browser window before regression coverage can be claimed.

Second run [41702499653](https://github.com/gakera/zen-window-sync-canary/actions/runs/41702499653) confirmed a visible fixture and trusted click after bypassing onboarding. Zen explicitly rejects WebDriver's New Window endpoint (`openWindow() not supported in Zen`). The next probe uses the standard Ctrl+N keyboard action, waits up to 15 seconds for a new handle, and attempts switching. Screenshots are saved before window creation and in the second window as well as on failure. This workaround is experimental until runner evidence confirms it.

First Windows run [41702080529](https://github.com/gakera/zen-window-sync-canary/actions/runs/41702080529) successfully extracted verified Zen 1.24b and established a headed WebDriver session. The first click failed with `element not interactable`; screenshot capture reported a 0×0 content area. Result: UNVERIFIED, before any sync assertion. The next attempt sets the release's `zen.welcome-screen.seen` preference to bypass first-run onboarding (whose source hides browser content), sets the window dimensions, and logs viewport dimensions and full WebDriver errors. Onboarding is a suspected cause, pending confirmation by the rerun.

1. Publishing and manual Windows execution were approved and completed. No dependencies were installed on Mac.
2. Inspect actual Windows results. If WebDriver fails, investigate supported Windows accessibility/UI automation and prove real control on the hosted desktop. Do not expand the suite while automation is unusable.
3. The focused same-tab scenario is implemented. The 1.24b run failed at the first destination live-state assertion, so the later fresh-click and return-to-A assertions did not run. Verify those remaining steps against a release that successfully transfers content.
4. Use PASS only when every required behavior executes successfully, FAIL only for demonstrated behavioral assertion failures, UNVERIFIED for setup/automation/evidence failures. P0 alone cannot produce PASS or FAIL.
5. Validate sensitivity using reported historical versions 1.21.8b and 1.21.9b from [issue 14759](https://github.com/zen-browser/desktop/issues/14759); these are user reports, not independently verified controls.
6. Then add daily Ubuntu release discovery at 06:17 UTC, durable deduplication by release ID + asset digest + suite revision, manual retest, and Windows jobs only for new identities. Document scheduled-workflow inactivity and stale results. No generated-result commits without approval.
