"""Local entrypoint for the streaming node (runs on IMX93 in production).

Run:
    cd streaming_web
    python local_host.py

In another terminal:
    ngrok http 5001

Then put the ngrok https URL into linebot/.env's STREAM_PUBLIC_BASE_URL.
STREAM_SIGNING_KEY in this node's .env must match linebot's.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

load_dotenv(HERE / ".env")

if not os.getenv("STREAM_SIGNING_KEY"):
    print("[warn] STREAM_SIGNING_KEY not set — token verification will fail.")
    print("       copy .env.example to .env and fill it in (must match linebot's).")

from app import create_app  # noqa: E402

app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    print(f"\nstreaming_web listening on http://localhost:{port}")
    print(f"  stream  : GET  /stream?token=<JWT>     (MJPEG)")
    print(f"  snap    : GET  /snapshot?token=<JWT>   (JPEG)")
    print(f"  health  : GET  /healthz")
    print(f"  -> run `ngrok http {port}` and set the URL into linebot's STREAM_PUBLIC_BASE_URL\n")
    app.run(host="0.0.0.0", port=port, threaded=True, debug=True)
