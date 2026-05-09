"""Local entrypoint (for testing the LINE bot half before/without deploying
to Cloud Function).

Run:
    cd linebot
    python local_host.py

Architecture: this node only handles LINE webhook + /event. The streaming
endpoints live in streaming_web/. STREAM_PUBLIC_BASE_URL must point at
the streaming_web node's public URL (its ngrok tunnel).

Note: this folder is named `linebot/` to match the user's request, but the
LINE SDK also imports as `linebot.v3.*`. To avoid the name collision we do
NOT make this folder a Python package (no __init__.py) and we run scripts
from inside it so Python's sys.path[0] is this directory and sibling modules
import cleanly while the installed `linebot` SDK still resolves via
site-packages.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

load_dotenv(HERE / ".env")

REQUIRED = [
    "LINE_CHANNEL_SECRET",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "STREAM_SIGNING_KEY",
    "STREAM_PUBLIC_BASE_URL",
]
missing = [k for k in REQUIRED if not os.getenv(k)]
if missing:
    print(f"[warn] missing required env vars: {missing}")
    print("       copy .env.example to .env and fill them in.")

if not os.getenv("LINE_USER_ID"):
    print(
        "[info] LINE_USER_ID not set yet. Add the bot as a friend, send any "
        "message, copy the userId from the bot's reply, paste into .env, "
        "then restart."
    )

from app import create_app  # noqa: E402

app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print(f"\nLINE bot listening on http://localhost:{port}")
    print(f"  webhook : POST /webhook   (set Cloud Function URL in LINE console)")
    print(f"  trigger : POST /event     body: {{\"event_type\": \"fall\"}}")
    print(f"  health  : GET  /healthz")
    print(f"  stream  : -> handled by streaming_web (STREAM_PUBLIC_BASE_URL)\n")
    app.run(host="0.0.0.0", port=port, threaded=True, debug=True)
