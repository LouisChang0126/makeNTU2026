"""Event-trigger entrypoint.

Usage from another Python script (run from inside linebot/ directory or with
PYTHONPATH including it):

    from notifier import trigger_event
    trigger_event("fall")

Or via HTTP: POST /event {"event_type": "fall"}.

Streaming token is a JWT (HS256) signed with STREAM_SIGNING_KEY. The
streaming_web node verifies it independently — no shared state.
"""
from datetime import datetime, timezone

import jwt as pyjwt
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    ImageMessage,
    MessagingApi,
    MulticastRequest,
    TextMessage,
)

import config

EVENT_LABELS = {
    "fall": "跌倒",
    "help": "求救",
}


def _sign_token(ttl_seconds: int) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"iat": now, "exp": now + ttl_seconds}
    return pyjwt.encode(payload, config.stream_signing_key(), algorithm="HS256")


def trigger_event(event_type: str = "fall") -> dict:
    """Sign a JWT, push LINE alert, return the URLs.

    Returns:
        {"token": str, "stream_url": str, "snapshot_url": str, "ttl_seconds": int}
    """
    ttl = config.stream_ttl_seconds()
    base = config.stream_public_base_url()
    user_ids = config.line_user_ids()

    token = _sign_token(ttl)
    stream_url = f"{base}/stream?token={token}"
    snapshot_url = f"{base}/snapshot?token={token}"

    label = EVENT_LABELS.get(event_type, event_type)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"⚠️ 偵測到{label}事件\n"
        f"時間：{ts}\n\n"
        f"2 小時內可查看即時影像：\n{stream_url}"
    )

    cfg = Configuration(access_token=config.channel_access_token())
    with ApiClient(cfg) as client:
        api = MessagingApi(client)
        api.multicast(
            MulticastRequest(
                to=user_ids,
                messages=[
                    TextMessage(text=text),
                    ImageMessage(
                        original_content_url=snapshot_url,
                        preview_image_url=snapshot_url,
                    ),
                ],
            )
        )

    return {
        "token": token,
        "stream_url": stream_url,
        "snapshot_url": snapshot_url,
        "ttl_seconds": ttl,
        "recipients": len(user_ids),
    }
