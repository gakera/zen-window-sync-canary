import base64
import hashlib
import http.server
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile


def request_json(url, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {
        "User-Agent": "zen-window-sync-canary",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json" if "api.github.com/" in url else "application/json",
    }
    if urllib.parse.urlparse(url).hostname == "api.github.com" and os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error


def release_asset(release, name):
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("A published stable release is required")
    matches = [asset for asset in release["assets"] if asset["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} asset")
    asset = matches[0]
    if not asset.get("digest", "").startswith("sha256:"):
        raise ValueError("Published SHA-256 digest is required")
    return asset


def download(asset, target):
    url = asset["browser_download_url"]
    if not url.startswith("https://github.com/"):
        raise ValueError("Unexpected download origin")
    with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)
    with target.open("rb") as downloaded:
        digest = "sha256:" + hashlib.file_digest(downloaded, "sha256").hexdigest()
    if digest != asset["digest"]:
        raise ValueError("Downloaded asset digest mismatch")


class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = (Path(__file__).parent / "fixture.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def wait_ready(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("geckodriver exited before becoming ready")
        try:
            if request_json(url)["value"]["ready"]:
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.2)
    raise TimeoutError("geckodriver readiness timeout")


def browser_windows(process_id):
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    windows = []

    @callback_type
    def collect(handle, parameter):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
        name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(handle, name, len(name))
        if owner.value == process_id and user32.IsWindowVisible(handle) and name.value == "MozillaWindowClass":
            windows.append(int(handle))
        return True

    user32.EnumWindows(collect, 0)
    return windows


def main():
    evidence = Path("evidence")
    evidence.mkdir(exist_ok=True)
    report = {
        "classification": "UNVERIFIED",
        "reason": "P0 does not yet exercise synchronized tab state",
        "p0_complete": False,
        "stage": "platform",
        "os": platform.platform(),
        "suite_revision": os.getenv("GITHUB_SHA", "local"),
        "runner_image": os.getenv("ImageVersion"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    driver_process = None
    server = None
    session_url = None

    def stage(name):
        report["stage"] = name
        print(time.strftime("%H:%M:%S UTC", time.gmtime()) + " | " + name, flush=True)

    with tempfile.TemporaryDirectory(prefix="zen-canary-") as temporary:
        root = Path(temporary)
        try:
            if platform.system() != "Windows":
                raise RuntimeError("This feasibility probe requires Windows")
            stage("release_discovery")
            tag = os.getenv("ZEN_RELEASE", "latest")
            endpoint = "latest" if tag == "latest" else "tags/" + urllib.parse.quote(tag, safe="")
            release = request_json("https://api.github.com/repos/zen-browser/desktop/releases/" + endpoint)
            asset = release_asset(release, "zen.installer.exe")
            report["release"] = {"tag": release["tag_name"], "id": release["id"], "asset_id": asset["id"], "asset": asset["name"], "digest": asset["digest"]}
            print("Selected Zen " + release["tag_name"] + "; verifying " + asset["name"], flush=True)
            stage("download_extract")
            installer = root / "zen.installer.exe"
            download(asset, installer)
            with (evidence / "extraction.log").open("w") as log:
                subprocess.run(["7z", "x", str(installer), "-o" + str(root / "zen"), "-y"], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
            binaries = list((root / "zen").rglob("zen.exe"))
            if len(binaries) != 1:
                raise RuntimeError("Installer extraction did not produce exactly one zen.exe")
            binary = binaries[0]
            distribution = binary.parent / "distribution"
            distribution.mkdir(exist_ok=True)
            (distribution / "policies.json").write_text(json.dumps({"policies": {"DisableAppUpdate": True, "DisableTelemetry": True, "DontCheckDefaultBrowser": True}}))
            driver_release = request_json("https://api.github.com/repos/mozilla/geckodriver/releases/tags/v0.37.1")
            driver_asset = release_asset(driver_release, "geckodriver-v0.37.1-win64.zip")
            report["driver"] = {"tag": driver_release["tag_name"], "digest": driver_asset["digest"]}
            driver_zip = root / "driver.zip"
            download(driver_asset, driver_zip)
            with zipfile.ZipFile(driver_zip) as archive:
                (root / "geckodriver.exe").write_bytes(archive.read("geckodriver.exe"))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            stage("webdriver_session")
            with (evidence / "geckodriver.log").open("w") as log:
                driver_process = subprocess.Popen([str(root / "geckodriver.exe"), "--port", str(port), "--log", "trace"], stdout=log, stderr=subprocess.STDOUT)
                base_url = f"http://127.0.0.1:{port}"
                wait_ready(base_url + "/status", driver_process)
                profile = root / "profile"
                profile.mkdir()
                session = request_json(base_url + "/session", {"capabilities": {"alwaysMatch": {"browserName": "firefox", "moz:firefoxOptions": {"binary": str(binary), "args": ["-no-remote", "-profile", str(profile)], "prefs": {"zen.welcome-screen.seen": True, "zen.window-sync.enabled": True, "zen.urlbar.replace-newtab": False, "browser.shell.checkDefaultBrowser": False}}}}})["value"]
                session_url = base_url + "/session/" + session["sessionId"]
                report["capabilities"] = session["capabilities"]

                def command(path, payload=None, method=None):
                    return request_json(session_url + path, payload, method)["value"]

                stage("click_and_window_switch")
                command("/window/rect", {"width": 1200, "height": 800})
                command("/url", {"url": f"http://127.0.0.1:{server.server_port}/"})
                viewport = command("/execute/sync", {"script": "return {width: innerWidth, height: innerHeight, visibility: document.visibilityState}", "args": []})
                report["viewport"] = viewport
                print("Fixture viewport: " + json.dumps(viewport), flush=True)
                first = command("/window")
                button = command("/element", {"using": "css selector", "value": "#increment"})
                command("/element/" + button["element-6066-11e4-a52e-4f735466cecf"] + "/click", {})
                state = command("/execute/sync", {"script": "return window.snapshot()", "args": []})
                if state["counter"] != 1 or not state["trustedClick"] or state["visibility"] != "visible":
                    raise RuntimeError("P0 real-click/visibility evidence unavailable")
                report["first_click"] = state
                (evidence / "before-new-window.png").write_bytes(base64.b64decode(command("/screenshot")))
                stage("new_window_shortcut")
                previous_handles = set(command("/window/handles"))
                browser_pid = session["capabilities"]["moz:processID"]
                report["native_windows_before"] = browser_windows(browser_pid)
                subprocess.run([
                    "powershell.exe", "-NoProfile", "-File",
                    str(Path(__file__).parent / "open-window.ps1"),
                    "-BrowserProcessId", str(browser_pid),
                ], check=True, timeout=15)
                deadline = time.monotonic() + 15
                second = None
                while time.monotonic() < deadline:
                    new_handles = set(command("/window/handles")) - previous_handles
                    if new_handles and len(browser_windows(browser_pid)) == 2:
                        break
                    time.sleep(0.2)
                report["native_windows_after"] = browser_windows(browser_pid)
                report["new_tab_handles"] = sorted(new_handles)
                print("Native browser windows: " + json.dumps(report["native_windows_after"]), flush=True)
                if len(report["native_windows_before"]) != 1 or len(report["native_windows_after"]) != 2:
                    raise RuntimeError("Expected one native browser window before Ctrl+N and two afterward")
                command("/window", {"handle": first})
                baseline_rect = command("/window/rect", {"x": 10, "y": 10, "width": 1100, "height": 750})
                for candidate in sorted(new_handles):
                    command("/window", {"handle": candidate})
                    candidate_rect = command("/window/rect", {"x": 180, "y": 100, "width": 1000, "height": 650})
                    command("/window", {"handle": first})
                    source_rect = command("/window/rect")
                    if source_rect == baseline_rect and candidate_rect != baseline_rect:
                        second = candidate
                        break
                    baseline_rect = command("/window/rect", {"x": 10, "y": 10, "width": 1100, "height": 750})
                if second is None:
                    raise RuntimeError("Could not map a new tab handle to the independent second browser window")
                print("Confirmed second native browser window and independent window geometry", flush=True)
                report["window_creation"] = "Native Windows Ctrl+N via WScript.Shell"
                stage("switch_second_window")
                command("/window", {"handle": second})
                command("/url", {"url": f"http://127.0.0.1:{server.server_port}/?second"})
                (evidence / "second-window.png").write_bytes(base64.b64decode(command("/screenshot")))
                command("/window", {"handle": first})
                report["returned_window"] = command("/window")
                if report["returned_window"] != first or second == first:
                    raise RuntimeError("Window switching could not be confirmed")
                (evidence / "browser.png").write_bytes(base64.b64decode(command("/screenshot")))
                report["p0_complete"] = True
                stage("p0_complete")
        except Exception:
            report["error"] = traceback.format_exc()
            print(report["error"], flush=True)
            if session_url:
                try:
                    screenshot = request_json(session_url + "/screenshot")["value"]
                    (evidence / "failure.png").write_bytes(base64.b64decode(screenshot))
                except Exception:
                    pass
        finally:
            if session_url:
                try:
                    request_json(session_url, method="DELETE")
                except Exception:
                    pass
            if driver_process and driver_process.poll() is None:
                try:
                    subprocess.run(["taskkill", "/PID", str(driver_process.pid), "/T", "/F"], capture_output=True, timeout=15)
                except Exception:
                    report["cleanup_error"] = traceback.format_exc()
            if server:
                server.shutdown()
            (evidence / "report.json").write_text(json.dumps(report, indent=2))
            summary = f"## UNVERIFIED\n\nP0 completed: {report['p0_complete']}\n\nStage: {report['stage']}\n\n{report['reason']}\n"
            (evidence / "summary.md").write_text(summary)
            print(summary, flush=True)
            if os.getenv("GITHUB_STEP_SUMMARY"):
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as output:
                    output.write(summary)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
