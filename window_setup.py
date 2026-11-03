import time


def open_second_window(observe, send, record, attempts=3, timeout=10):
    initial = observe()
    original_handles = set(initial["tabs"])
    if len(initial["native"]) != 1 or len(initial["chrome"]) != 1:
        raise RuntimeError("Window setup requires exactly one initial native and browser-UI window")

    def status(state):
        native_count = len(state["native"])
        chrome_count = len(state["chrome"])
        if native_count > 2 or chrome_count > 2:
            raise RuntimeError("Unexpected extra windows; refusing another New Window action")
        if native_count == 0 or chrome_count == 0:
            raise RuntimeError("Original browser window disappeared")
        new_tabs = set(state["tabs"]) - original_handles
        if native_count == 2 and chrome_count == 2 and new_tabs:
            return "complete"
        if native_count == 1 and chrome_count == 1 and not new_tabs:
            return "unchanged"
        return "pending"

    for attempt in range(1, attempts + 1):
        before = observe()
        before_status = status(before)
        if before_status == "complete":
            record({"attempt": attempt, "result": "late_window_detected", "state": before})
            return initial, before
        entry = {"attempt": attempt, "before": before, "sent": False}
        if before_status == "unchanged":
            try:
                send()
                entry["sent"] = True
            except Exception as error:
                entry["send_error"] = str(error)
        deadline = time.monotonic() + timeout
        after = before
        while time.monotonic() < deadline:
            after = observe()
            if status(after) == "complete":
                entry.update(result="complete", after=after)
                record(entry)
                return initial, after
            time.sleep(0.2)
        entry.update(result="timeout", after=after)
        record(entry)
        if status(after) != "unchanged":
            raise RuntimeError("Partially created window; refusing to send a duplicate New Window action")
    raise TimeoutError(f"Second window did not appear after {attempts} bounded setup attempts")
