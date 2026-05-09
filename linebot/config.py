"""Centralized environment access. Call after dotenv has been loaded."""
import os


def channel_secret() -> str:
    return os.environ["LINE_CHANNEL_SECRET"]


def channel_access_token() -> str:
    return os.environ["LINE_CHANNEL_ACCESS_TOKEN"]


def line_user_id() -> str:
    return os.environ["LINE_USER_ID"]


def stream_signing_key() -> str:
    return os.environ["STREAM_SIGNING_KEY"]


def stream_public_base_url() -> str:
    return os.environ["STREAM_PUBLIC_BASE_URL"].rstrip("/")


def stream_ttl_seconds() -> int:
    return int(os.getenv("STREAM_TTL_SECONDS", "7200"))


def port() -> int:
    return int(os.getenv("PORT", "5000"))
