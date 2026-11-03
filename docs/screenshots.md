# README screenshot evidence

The README's passing/failing pair was reviewed and approved by the repository owner before inclusion. Both images are unedited full-desktop PNGs from disposable GitHub-hosted Windows runners, captured on 2026-11-03 using the same test revision, `cc2c028`.

| Image | Release | Source run | Original artifact filename |
| --- | --- | --- | --- |
| [Working shared tab](images/zen-1.21.8b-pass.png) | 1.21.8b | [41712798681](https://github.com/gakera/zen-window-sync-canary/actions/runs/41712798681) | `desktop-clean-comparison.png` |
| [Blank shared tab](images/zen-1.24b-fail.png) | 1.24b | [41712794002](https://github.com/gakera/zen-window-sync-canary/actions/runs/41712794002) | `desktop-clean-comparison.png` |

## Reading the comparison

The same fixture is opened once from a link in window A. The test records its shared tab ID, counter, per-document page ID, scroll and history state. A then selects **Other page**, and B selects the matching shared tab through normal browser UI input.

- **1.21.8b:** the entire scenario passes, including a trusted click in B and the updated live state back in A. The presentation capture then shows the shared page in B with counter 2, scroll 1400 px and the same document ID.
- **1.24b:** the first destination-state assertion fails. B displays a visible, empty `about:blank` document, without the expected page ID, counter or history URL. The selected tab's shared ID matches A's fixture tab even though its label has changed to **New Tab**.

After recording each verdict, the presentation step closes unrelated setup tabs through normal UI input, retaining the shared page and **Other page**. It rechecks that the passing live state or observed blank failure remains before saving the clean capture. This step does not overwrite the verdict; original pre-cleanup screenshots and state observations are also retained in the run artifacts.

The taskbar and Windows pinning prompt belong to the runner desktop. No screenshots of a maintainer's personal desktop are included. Images are committed here so the illustration remains available after the original seven-day Actions artifacts expire.
