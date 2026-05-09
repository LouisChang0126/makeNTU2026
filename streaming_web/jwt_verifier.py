"""JWT verification for incoming /stream and /snapshot requests.

The linebot node signs JWT (HS256) with STREAM_SIGNING_KEY; this node uses
the same key to verify. PyJWT's decode() automatically rejects expired tokens
when the payload contains 'exp'.
"""
import jwt as pyjwt

import config


class TokenError(Exception):
    pass


def verify(token: str) -> dict:
    if not token:
        raise TokenError("missing token")
    try:
        return pyjwt.decode(token, config.stream_signing_key(), algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise TokenError("expired")
    except pyjwt.InvalidTokenError as e:
        raise TokenError(f"invalid: {e}")
