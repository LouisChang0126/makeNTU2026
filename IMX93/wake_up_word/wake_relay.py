"""HTTP relay running on the laptop that bridges Ubuntu (WiFi) and IMX93 (USB net).

The laptop is on both the home WiFi and the IMX93's USB-Ethernet subnet.
IMX93 cannot reach Ubuntu directly, so it talks to this relay, which
forwards each request to the real wake_server on Ubuntu.

Forwarded endpoints
    GET  /wake_status   /wake_peek   /healthz
    POST /play

Usage
    UPSTREAM=http://192.168.1.10:8765 python wake_relay.py --host 0.0.0.0 --port 8765
"""
import argparse
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = os.environ.get("UPSTREAM", "http://192.168.1.10:8765")
GET_TIMEOUT_S = 1.0
POST_TIMEOUT_S = 15.0  # /play blocks until aplay finishes (audio can be ~10s)
ALLOWED_GET = ("/wake_status", "/wake_peek", "/healthz")
ALLOWED_POST = ("/play",)


class _Handler(BaseHTTPRequestHandler):
    def _send_raw(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_err(self, code: int, msg: str, extra: dict | None = None) -> None:
        body = {"error": msg}
        if extra:
            body.update(extra)
        self._send_raw(code, json.dumps(body).encode("utf-8"), "application/json")

    def do_GET(self):  # noqa: N802
        if self.path not in ALLOWED_GET:
            self._send_err(404, "not found")
            return
        url = f"{UPSTREAM.rstrip('/')}{self.path}"
        try:
            with urllib.request.urlopen(url, timeout=GET_TIMEOUT_S) as r:
                self._send_raw(
                    r.status, r.read(),
                    r.headers.get("Content-Type", "application/json"),
                )
        except (urllib.error.URLError, OSError) as e:
            # Fail closed with status=0 so an upstream outage cannot
            # silently cancel an alert (matches double_check semantics).
            self._send_err(503, str(e), extra={"status": 0})

    def do_POST(self):  # noqa: N802
        if self.path not in ALLOWED_POST:
            self._send_err(404, "not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        url = f"{UPSTREAM.rstrip('/')}{self.path}"
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=POST_TIMEOUT_S) as r:
                self._send_raw(
                    r.status, r.read(),
                    r.headers.get("Content-Type", "application/json"),
                )
        except (urllib.error.URLError, OSError) as e:
            self._send_err(503, str(e))

    def log_message(self, format, *args):
        return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    print(f">>> wake_relay listening on http://{args.host}:{args.port}, upstream={UPSTREAM}")
    ThreadingHTTPServer((args.host, args.port), _Handler).serve_forever()


if __name__ == "__main__":
    main()
