"""LINE webhook endpoint. Replies to any text message with the sender's
userId so you can paste it into .env's LINE_USER_ID.
"""
from flask import Blueprint, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

import config

bp = Blueprint("line", __name__)
_handler: WebhookHandler | None = None


def _build_handler() -> WebhookHandler:
    handler = WebhookHandler(config.channel_secret())

    @handler.add(MessageEvent, message=TextMessageContent)
    def _on_text(event):
        user_id = event.source.user_id if event.source else "(unknown)"
        text = (
            f"Your LINE userId:\n{user_id}\n\n"
            "請複製貼到 .env 的 LINE_USER_ID 後重啟服務"
        )
        cfg = Configuration(access_token=config.channel_access_token())
        with ApiClient(cfg) as client:
            api = MessagingApi(client)
            api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=text)],
                )
            )

    return handler


def get_handler() -> WebhookHandler:
    global _handler
    if _handler is None:
        _handler = _build_handler()
    return _handler


@bp.post("/webhook")
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        get_handler().handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"
