import base64
import json
from pathlib import Path
import subprocess
import time


class RegressionFailure(Exception):
    pass


def state_differences(expected, actual):
    differences = []
    for field in ("token", "counter", "url"):
        if actual.get(field) != expected[field]:
            differences.append(f"{field}: expected {expected[field]!r}, observed {actual.get(field)!r}")
    if abs(actual.get("scroll", -9999) - expected["scroll"]) > 4:
        differences.append(f"scroll: expected {expected['scroll']}, observed {actual.get('scroll')}")
    if actual.get("visibility") != "visible" or actual.get("width", 0) <= 0 or actual.get("height", 0) <= 0:
        differences.append("fixture has no visible viewport")
    return differences


def until(predicate, description, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.2)
    raise TimeoutError(description)


def run_sync_test(command, desktop, stage, report, evidence, browser_pid, source_hwnd, port, events):
    stage("sync_ui_setup")

    def context(name):
        command("/moz/context", {"context": name})

    def script(code, *arguments):
        return command("/execute/sync", {"script": code, "args": list(arguments)})

    def inventory():
        return script("return Array.from(gBrowser.tabs, tab => ({id: tab.id, label: tab.label, selected: tab.selected, empty: tab.hasAttribute('zen-empty-tab'), url: tab.linkedBrowser?.currentURI?.spec}));")

    def click(selector):
        element = command("/element", {"using": "css selector", "value": selector})
        command("/element/" + element["element-6066-11e4-a52e-4f735466cecf"] + "/click", {})

    def open_native(path):
        context("chrome")
        command("/window", {"handle": source_window})
        subprocess.run([
            "powershell.exe", "-NoProfile", "-File", str(Path(__file__).parent / "open-window.ps1"),
            "-BrowserProcessId", str(browser_pid), "-WindowHandle", str(source_hwnd),
            "-NewTabOnly",
        ], check=True, timeout=20)
        address = command("/element", {"using": "css selector", "value": "#urlbar-input"})
        address_id = address["element-6066-11e4-a52e-4f735466cecf"]
        command("/element/" + address_id + "/click", {})
        command("/element/" + address_id + "/clear", {})
        command("/element/" + address_id + "/value", {"text": f"http://127.0.0.1:{port}/{path}"})
        command("/element/" + address_id + "/value", {"text": "\ue007"})

    def select_tab(window_handle, tab_id):
        context("chrome")
        command("/window", {"handle": window_handle})
        click('[id=' + json.dumps(tab_id) + ']')
        until(lambda: script("return gBrowser.selectedTab.id") == tab_id, "UI click did not select the intended shared tab")
        report.setdefault("selections", []).append({"window": window_handle, "tab_id": tab_id})

    def selected_content():
        selected = script("const { NavigableManager } = ChromeUtils.importESModule('chrome://remote/content/shared/NavigableManager.sys.mjs'); return {tab_id: gBrowser.selectedTab.id, handle: NavigableManager.getIdForBrowser(gBrowser.selectedBrowser)};")
        if not selected["handle"]:
            raise RuntimeError("Selected browser tab has no WebDriver content handle")
        context("content")
        command("/window", {"handle": selected["handle"]})
        context("chrome")
        if script("return gBrowser.selectedTab.id") != selected["tab_id"]:
            raise RuntimeError("Binding WebDriver content unexpectedly changed the UI-selected tab")
        report.setdefault("content_bindings", []).append(selected)
        context("content")

    def observe():
        return script("return typeof window.snapshot === 'function' ? window.snapshot() : {url: location.href, title: document.title, readyState: document.readyState, visibility: document.visibilityState, width: innerWidth, height: innerHeight, text: document.body?.innerText?.slice(0,500)}")

    def check_state(expected, label):
        actual = {}
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            actual = observe()
            if not state_differences(expected, actual):
                break
            time.sleep(0.2)
        report[label] = actual
        print(label + ": " + json.dumps(actual), flush=True)
        desktop("desktop-" + label + ".png")
        try:
            (evidence / (label + ".png")).write_bytes(base64.b64decode(command("/screenshot")))
        except Exception as error:
            report.setdefault("page_capture_errors", []).append(str(error))
        differences = state_differences(expected, actual)
        if differences:
            raise RegressionFailure(label + ": " + "; ".join(differences))

    context("chrome")
    source_window = command("/window")
    windows = command("/window/handles")
    report["chrome_windows"] = windows
    if len(windows) != 2 or source_window not in windows:
        raise RuntimeError("Browser UI mode did not expose exactly two actual browser windows")
    target_window = next(handle for handle in windows if handle != source_window)
    command("/execute/async", {"script": "const done = arguments[arguments.length - 1]; Promise.all([gZenWorkspaces.promiseInitialized, gZenStartup.promiseInitialized]).then(() => done(true), error => done({error: String(error)}));", "args": []})
    prefs = script("return {enabled: Services.prefs.getBoolPref('zen.window-sync.enabled'), onlyPinned: Services.prefs.getBoolPref('zen.window-sync.sync-only-pinned-tabs')};")
    report["sync_preferences"] = prefs
    if not prefs["enabled"] or prefs["onlyPinned"]:
        raise RuntimeError("Required normal-tab synchronization preferences are not active")
    open_native("sync-fixture")
    command("/window", {"handle": source_window})
    fixture_url = f"http://127.0.0.1:{port}/sync-fixture"
    try:
        tab = until(lambda: next((tab for tab in inventory() if tab["url"] == fixture_url and tab["selected"] and not tab["empty"] and tab["id"]), None), "Normal address-bar navigation did not produce a materialized fixture tab")
    finally:
        report["source_tabs_after_navigation"] = inventory()
    shared_id = tab["id"]
    report["shared_tab_id"] = shared_id
    report["source_tabs_initial"] = inventory()
    print("Materialized fixture tab: " + shared_id, flush=True)
    selected_content()
    if command("/url") != fixture_url:
        raise RuntimeError("WebDriver content context did not follow the selected fixture tab")
    click("#increment")
    click("#history")
    command("/actions", {"actions": [{"type": "wheel", "id": "scroll", "actions": [{"type": "scroll", "x": 500, "y": 400, "deltaX": 0, "deltaY": 700, "duration": 300, "origin": "viewport"}]}]})
    expected = until(lambda: (state if (state := observe()).get("scroll", 0) >= 500 else None), "Fixture did not scroll")
    if expected.get("counter") != 1 or not expected.get("trustedClick") or "?state=1" not in expected.get("url", ""):
        raise RuntimeError("Source fixture live-state setup did not complete")
    report["expected_state"] = expected
    desktop("desktop-sync-source-state.png")
    stage("sync_deselect_source")
    open_native("distractor")
    context("chrome")
    command("/window", {"handle": source_window})
    distractor = until(lambda: next((tab for tab in inventory() if tab["selected"] and tab["url"].endswith("/distractor") and not tab["empty"]), None), "Source window did not select the distractor tab")
    report["source_tabs_deselected"] = inventory()
    command("/window", {"handle": target_window})
    try:
        until(lambda: any(tab["id"] == shared_id for tab in inventory()), "Shared fixture tab absent in second window")
    except TimeoutError as error:
        report["target_tabs"] = inventory()
        raise RegressionFailure(str(error)) from error
    report["target_tabs"] = inventory()
    stage("sync_select_target")
    select_tab(target_window, shared_id)
    selected_content()
    check_state(expected, "sync-target-state")
    click("#increment")
    expected = dict(expected, counter=2)
    check_state(expected, "sync-target-after-click")
    until(lambda: any(event.get("token") == expected["token"] and event.get("counter") == 2 and event.get("trustedClick") for event in events), "Server did not observe a fresh trusted click in the target window")
    report["fixture_events"] = list(events)
    stage("sync_return_source")
    select_tab(target_window, distractor["id"])
    select_tab(source_window, shared_id)
    selected_content()
    check_state(expected, "sync-return-state")
    report["sync_scenario_complete"] = True
    stage("sync_complete")
