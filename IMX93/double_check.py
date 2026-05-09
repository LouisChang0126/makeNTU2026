"""10-second cancel window before alerting family.

Plays a prompt over the speaker and polls the remote wake-word server
(running on the Ubuntu PC) for the cancel keyword (status==2). If no
cancel arrives in CANCEL_WINDOW_S, posts to the GCF /event endpoint to
trigger the LINE notification.

Set WAKE_ENDPOINT to the Ubuntu LAN URL, e.g.
    export WAKE_ENDPOINT=http://192.168.1.10:8765
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

GCF_ENDPOINT = "https://makentu2026-linebot-129834734368.asia-east1.run.app/event"
CANCEL_WINDOW_S = 10.0
POLL_INTERVAL_S = 0.1
HTTP_TIMEOUT_S = 10.0

WAKE_ENDPOINT = os.environ.get("WAKE_ENDPOINT", "http://192.168.1.10:8765")
WAKE_HTTP_TIMEOUT_S = 0.5

AUDIO_DIR = Path(__file__).parent / "audio"
PROMPT_AUDIO = AUDIO_DIR / "prompt.wav"        # 偵測到您可能跌倒，請問你還好嗎？請回應是否須取消通知
ALERTED_AUDIO = AUDIO_DIR / "alerted.wav"      # 已通知您的家人，請保持冷靜，等待協助
CANCELLED_AUDIO = AUDIO_DIR / "cancelled.wav"  # 好的，已為您取消通知，請注意安全


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


def _play(path: Path) -> None:
    if not path.exists():
        print(f"[audio] missing file: {path}")
        return
    subprocess.run(["aplay", "-q", str(path)], check=False)


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

    _play(PROMPT_AUDIO)

    deadline = time.monotonic() + CANCEL_WINDOW_S
    while time.monotonic() < deadline:
        if wake_getter() == 2:
            _play(CANCELLED_AUDIO)
            return False  # 使用者取消，回傳 False
        time.sleep(POLL_INTERVAL_S)

    try:
        _post_event(event_type)
        _play(ALERTED_AUDIO)
        return True   # 正式發出通知，回傳 True
    except Exception as e:
        print(f"[gcf] post failed: {e}")
        return False  # 發送失敗，不進入冷卻
