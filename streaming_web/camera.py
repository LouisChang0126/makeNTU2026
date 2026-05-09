"""Webcam capture. On IMX93 swap WebcamSource for an IMX93Source (RTSP/HTTP)
implementing the same get_jpeg() / generate_mjpeg() methods.
"""
import threading
import time

import cv2

import config


class WebcamSource:
    def __init__(self, index: int = 0):
        self._index = index
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()

    def _ensure_open(self) -> cv2.VideoCapture:
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self._index, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open camera index {self._index}")
        return self._cap

    def get_jpeg(self, quality: int = 80) -> bytes:
        with self._lock:
            cap = self._ensure_open()
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("camera read failed")
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ok:
                raise RuntimeError("jpeg encode failed")
            return buf.tobytes()

    def generate_mjpeg(self, fps: int = 15):
        interval = 1.0 / max(fps, 1)
        boundary = b"--frame"
        while True:
            try:
                jpg = self.get_jpeg()
            except Exception:
                break
            yield boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: " \
                + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n"
            time.sleep(interval)


_camera: WebcamSource | None = None
_camera_lock = threading.Lock()


def get_camera() -> WebcamSource:
    global _camera
    with _camera_lock:
        if _camera is None:
            _camera = WebcamSource(config.camera_index())
        return _camera
