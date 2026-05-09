"""10-second cancel window before alerting family.

Plays a prompt over the speaker and listens to the wake-word getter for the
cancel keyword (output==2). If no cancel arrives in CANCEL_WINDOW_S, posts
to the GCF /event endpoint to trigger the LINE notification.
"""
import json
import platform
import subprocess
import time
import urllib.request
from pathlib import Path

from 喚醒詞 import getter as wake_getter

GCF_ENDPOINT = "https://makentu2026-linebot-129834734368.asia-east1.run.app/event"
CANCEL_WINDOW_S = 10.0
POLL_INTERVAL_S = 0.1
HTTP_TIMEOUT_S = 10.0

AUDIO_DIR = Path(__file__).parent / "audio"
PROMPT_AUDIO = AUDIO_DIR / "prompt.wav"        # 偵測到您可能跌倒，您還好嗎？10 秒內回應否取消通知
ALERTED_AUDIO = AUDIO_DIR / "alerted.wav"      # 已通知家人，請保持冷靜，等待協助
CANCELLED_AUDIO = AUDIO_DIR / "cancelled.wav"  # 好的，已為您取消通知，注意安全


def _play(path: Path) -> None:
    if not path.exists():
        print(f"[audio] missing file: {path}")
        return
    if platform.system() == "Windows":
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    else:
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


def confirm(event_type: str = "fall") -> None:
    _play(PROMPT_AUDIO)

    deadline = time.monotonic() + CANCEL_WINDOW_S
    while time.monotonic() < deadline:
        if wake_getter() == 2:
            _play(CANCELLED_AUDIO)
            return
        time.sleep(POLL_INTERVAL_S)

    try:
        _post_event(event_type)
    except Exception as e:
        print(f"[gcf] post failed: {e}")
    _play(ALERTED_AUDIO)
