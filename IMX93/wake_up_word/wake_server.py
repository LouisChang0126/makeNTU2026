"""HTTP wrapper that exposes wake_up.getter() and audio playback over the LAN.

Runs on the Ubuntu PC that owns both the microphone and the speaker.
The IMX93 polls GET /wake_status during double_check.confirm() to look for
the cancel keyword, and POSTs /play to drive prompt/alerted/cancelled
audio.

Endpoints
    GET  /wake_status   -> {"status": 0|1|2}    drain-and-reset
    GET  /wake_peek     -> {"status": 0|1|2}    read-only (debug/dashboard)
    GET  /healthz       -> {"ok": true}
    POST /play          body {"name": "prompt"|"alerted"|"cancelled"}
                        -> {"played": bool, "name": str}
                        Blocks until aplay finishes so callers can chain
                        prompt → wait-for-cancel → cancelled/alerted.

Env
    APLAY_DEVICE        Optional aplay -D device, e.g. plughw:CARD=Device

Usage
    cd IMX93
    python -m wake_up_word.wake_server --host 0.0.0.0 --port 8765
"""
import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Allow running as either `python -m wake_up_word.wake_server`
# or `python wake_up_word/wake_server.py`.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import wake_up  # noqa: E402

APLAY_DEVICE = os.environ.get("APLAY_DEVICE")
AUDIO_DIR = Path(_HERE).parent / "audio"
_AUDIO_FILES = {
    "prompt":    AUDIO_DIR / "prompt.wav",
    "alerted":   AUDIO_DIR / "alerted.wav",
    "cancelled": AUDIO_DIR / "cancelled.wav",
}


def _play_named(name: str) -> bool:
    path = _AUDIO_FILES.get(name)
    if path is None:
        print(f"[audio] unknown name: {name!r}")
        return False
    if not path.exists():
        print(f"[audio] missing file: {path}")
        return False
    cmd = ["aplay", "-q"]
    if APLAY_DEVICE:
        cmd += ["-D", APLAY_DEVICE]
    cmd.append(str(path))
    subprocess.run(cmd, check=False)
    return True


class _Handler(BaseHTTPRequestHandler):
    def _send(self, status_code: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler API)
        if self.path == "/wake_status":
            self._send(200, {"status": wake_up.getter()})
        elif self.path == "/wake_peek":
            self._send(200, {"status": wake_up._current_max_status})
        elif self.path == "/healthz":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/play":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid json"})
            return
        name = body.get("name", "")
        ok = _play_named(name)
        self._send(200 if ok else 400, {"played": ok, "name": name})

    def log_message(self, format, *args):
        # wake_up.main() already prints its own diagnostics; suppress per-request noise.
        return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    detector = threading.Thread(target=wake_up.main, daemon=True)
    detector.start()

    print(f">>> wake_server listening on http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), _Handler).serve_forever()


if __name__ == "__main__":
    main()
