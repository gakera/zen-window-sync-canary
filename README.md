# Zen Windows sync canary — P0 draft

Status: **UNVERIFIED** pending the first synchronized-state scenario run. P0 completed in [41703926147](https://github.com/gakera/zen-window-sync-canary/actions/runs/41703926147). See Actions for current logs and evidence. The probe prints timestamped milestones and errors; screenshots are saved as artifacts after the run.

## Focused synchronized-tab scenario

After P0, open a normal tab through native Ctrl+T and address-bar input. Read its shared Zen tab ID and inspect its counterpart in the other window using WebDriver browser-UI mode. Click the real sidebar tab through WebDriver's element-click endpoint; no script repairs or replaces Zen's synchronization logic. Browser-UI mode requires geckodriver's documented `--allow-system-access` flag, used only inside the disposable runner against the released binary. This is separate from in-tree Mochitest.

Mutate the fixture in A with a real counter click, history button and wheel scroll. Select a normal distractor tab in A before selecting the same shared fixture tab in B. Assert visible content, document token, counter, history URL and scroll; click again in B and require a server-observed trusted event. Deselect in B and return to A, checking the updated live state again. Save tab inventories, selected IDs, state observations, page screenshots and full desktop screenshots. A blank New Tab in B must fail this test even if the sidebar label or remembered URL looks correct.

PASS means this one required scenario completed; broader release safety and historical regression sensitivity remain unproven. FAIL means a behavioral mismatch after identifiable UI selection, including an absent mirrored tab after bounded polling. UNVERIFIED means required automation/setup/evidence did not complete. Expected failure on 1.24b is not overridden to green. Each manually dispatched run has its own runner VM and can execute concurrently.

The user expects the synchronized-state regression to fail on 1.24b. Treat 1.24b as an expected failing candidate, pending reproduction. Keep normal regression semantics: a confirmed state-loss assertion is FAIL, not an expected-failure override that makes the run green. A WebDriver failure is UNVERIFIED and supplies no evidence about the sync regression.

## First milestone

The manually triggered workflow downloads a real stable Windows x64 Zen installer, verifies its published SHA-256, extracts it with the runner's 7-Zip, disables updates in the disposable extracted application, and attempts a headed geckodriver session with a fresh temporary profile. No Python packages are required. It checks a trusted page click, visible document, creation of two window handles, window switching, and a screenshot. Installer extraction, first-run setup, and WebDriver support remain experimental until a Windows run succeeds.

The workflow always exits nonzero and reports UNVERIFIED at this phase, even if P0 completes. P0 success is automation evidence only; no release is certified safe. Errors identify their stage and retain trace logs. Runner timeout or setup failure may leave only partial evidence and must also be treated as UNVERIFIED. Artifacts expire after seven days; inspect them before sharing. They contain only a disposable local fixture, but driver traces include profile paths.

## Run locally

Screenshot scope: `browser.png`, `failure.png`, `before-new-window.png`, and `second-window.png` are WebDriver page viewport captures and exclude browser chrome. Files prefixed `desktop-` capture the entire Windows runner's virtual desktop, including browser frames, sidebar tabs, and any overlap. They show only the disposable CI desktop, never the user's Mac. Desktop capture errors are recorded separately in report.json.

`python3 -m unittest -v` runs release-selection checks on macOS without downloads or browser launch. `probe.py` runs only on Windows. It writes evidence/report.json and evidence/summary.md. Use workflow_dispatch with `latest` or an exact stable release tag. No schedule is enabled before feasibility is demonstrated.

## Verified research, 2026-11-03

- Mac: macOS 27.0.1 arm64, Command Line Tools installed, Homebrew 5.1.13, Git 2.54.0, gh 2.92.0, Python 3.11.8 with venv, Node 25.6.1, npm 11.9.0, /Applications/Zen.app present. No local geckodriver; none needed for authoring. Network-enabled gh auth status succeeds for gakera. No credentials are stored here.
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

1. Obtain approval to initialize Git, create gakera/zen-window-sync-canary with agreed visibility, commit/push this source, and dispatch one Windows run. No dependencies need installing on Mac.
2. Inspect actual Windows results. If WebDriver fails, investigate supported Windows accessibility/UI automation and prove real control on the hosted desktop. Do not expand the suite while automation is unusable.
3. After P0, implement the issue 14759 scenario: mutate counter, scroll, history and token in A; select another tab in A; select its synchronized counterpart in B through normal UI; verify visible live state and a fresh trusted click; return to A. Avoid the intentional preview when both windows select the same tab. The included fixture supplies state primitives but the synchronized-state regression is not implemented yet.
4. Use PASS only when every required behavior executes successfully, FAIL only for demonstrated behavioral assertion failures, UNVERIFIED for setup/automation/evidence failures. P0 cannot produce PASS or FAIL.
5. Validate sensitivity using reported historical versions 1.21.8b and 1.21.9b from [issue 14759](https://github.com/zen-browser/desktop/issues/14759); these are user reports, not independently verified controls.
6. Then add daily Ubuntu release discovery at 06:17 UTC, durable deduplication by release ID + asset digest + suite revision, manual retest, and Windows jobs only for new identities. Document scheduled-workflow inactivity and stale results. No generated-result commits without approval.
