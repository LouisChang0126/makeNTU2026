"""Centralized environment access. Call after dotenv has been loaded."""
import os


def stream_signing_key() -> str:
    return os.environ["STREAM_SIGNING_KEY"]


def camera_index() -> int:
    return int(os.getenv("CAMERA_INDEX", "0"))


def port() -> int:
    return int(os.getenv("PORT", "5001"))
