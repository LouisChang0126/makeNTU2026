"""Tiny LINE userId getter.

Run:
    cd lineid_getter
    python local_host.py

In another terminal:
    ngrok http 5000

Set LINE Developers Console -> Messaging API -> Webhook URL =
    https://<ngrok>.ngrok-free.app/webhook
Click Verify, enable Use webhook.

Then send any message from LINE; this terminal prints the sender's userId.
No signature verification, no reply — purely a debug tool.
"""
from datetime import datetime

from flask import Flask, request

app = Flask(__name__)


@app.post("/webhook")
def webhook():
    body = request.get_json(silent=True) or {}
    events = body.get("events", [])
    if not events:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] webhook ping (no events)")
    for event in events:
        ts = datetime.now().strftime("%H:%M:%S")
        etype = event.get("type", "?")
        src = event.get("source", {})
        user_id = src.get("userId", "?")
        if etype == "message":
            mtype = event.get("message", {}).get("type", "?")
            text = event.get("message", {}).get("text", "")
            print(f"[{ts}] {etype}/{mtype}  userId={user_id}  text={text!r}")
        else:
            print(f"[{ts}] {etype}  userId={user_id}")
    return "OK"


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    print("\nlineid_getter listening on http://localhost:5000")
    print("  webhook : POST /webhook  (set this URL via ngrok in LINE Console)")
    print("  -> send any LINE message, sender's userId will appear below\n")
    app.run(host="0.0.0.0", port=5000, threaded=True)
