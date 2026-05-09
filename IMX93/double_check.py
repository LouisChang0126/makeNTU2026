"""10-second cancel window before alerting family.

Polls the remote wake-word server (running on Ubuntu) for the cancel
keyword (status==2) and drives audio playback over the same HTTP server,
since the speaker is on the Ubuntu PC, not on IMX93. If no cancel arrives
in CANCEL_WINDOW_S, posts to the GCF /event endpoint to trigger the LINE
notification.

Set WAKE_ENDPOINT to whichever host is reachable from IMX93. With the
laptop relay in front of Ubuntu, that is the laptop's USB-side IP, e.g.
    export WAKE_ENDPOINT=http://192.168.7.1:8765
"""
import json
import os
import time
import urllib.error
import urllib.request

GCF_ENDPOINT = "https://makentu2026-linebot-129834734368.asia-east1.run.app/event"
CANCEL_WINDOW_S = 10.0
POLL_INTERVAL_S = 0.1
HTTP_TIMEOUT_S = 10.0

WAKE_ENDPOINT = os.environ.get("WAKE_ENDPOINT", "http://192.168.7.1:8765")
WAKE_HTTP_TIMEOUT_S = 0.5
PLAY_HTTP_TIMEOUT_S = 15.0  # /play blocks until aplay finishes


def wake_getter() -> int:
    """Drain-and-reset the remote wake-word status. Returns 0 on any network error
    so a flaky link cannot accidentally cancel the alert."""
    url = f"{WAKE_ENDPOINT.rstrip('/')}/wake_status"
    try:
        with urllib.request.urlopen(url, timeout=WAKE_HTTP_TIMEOUT_S) as resp:
            return int(json.loads(resp.read().decode("utf-8")).get("status", 0))
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"[wake] http get failed: {e}")
        return 0


def _play(name: str) -> None:
    """Tell the Ubuntu server to play one of: 'prompt', 'alerted', 'cancelled'.
    Blocks until playback finishes so the cancel window only opens after the
    prompt has actually been heard."""
    payload = json.dumps({"name": name}).encode("utf-8")
    url = f"{WAKE_ENDPOINT.rstrip('/')}/play"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=PLAY_HTTP_TIMEOUT_S) as resp:
            resp.read()
    except (urllib.error.URLError, OSError) as e:
        print(f"[audio] http play failed ({name}): {e}")


def _post_event(event_type: str) -> None:
    payload = json.dumps({"event_type": event_type}).encode("utf-8")
    req = urllib.request.Request(
        GCF_ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
        resp.read()


def confirm(event_type: str = "fall") -> bool:
    # Drain any wake-word state captured before the fall event so it
    # cannot pre-cancel the prompt that we are about to play.
    wake_getter()

    _play("prompt")

    deadline = time.monotonic() + CANCEL_WINDOW_S
    while time.monotonic() < deadline:
        if wake_getter() == 2:
            _play("cancelled")
            return False  # 使用者取消，回傳 False
        time.sleep(POLL_INTERVAL_S)

    try:
        _post_event(event_type)
        _play("alerted")
        return True   # 正式發出通知，回傳 True
    except Exception as e:
        print(f"[gcf] post failed: {e}")
        return False  # 發送失敗，不進入冷卻
