"""Flask app factory for the streaming node."""
from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    from stream import bp as stream_bp

    app.register_blueprint(stream_bp)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
