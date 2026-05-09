"""JWT-gated /stream and /snapshot endpoints."""
from flask import Blueprint, Response, abort, request

from camera import get_camera
import jwt_verifier

bp = Blueprint("stream", __name__)


def _check():
    token = request.args.get("token", "")
    try:
        jwt_verifier.verify(token)
    except jwt_verifier.TokenError:
        abort(410)


@bp.get("/stream")
def stream():
    _check()
    cam = get_camera()
    return Response(
        cam.generate_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@bp.get("/snapshot")
def snapshot():
    _check()
    cam = get_camera()
    try:
        jpeg = cam.get_jpeg()
    except RuntimeError as e:
        return {"error": str(e)}, 500
    return Response(jpeg, mimetype="image/jpeg")
