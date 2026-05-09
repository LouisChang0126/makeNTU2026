"""Flask app factory. Reused by local_host.py and main.py (Cloud Function)."""
from flask import Flask, jsonify, request


def create_app() -> Flask:
    app = Flask(__name__)

    from line_handler import bp as line_bp

    app.register_blueprint(line_bp)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.post("/event")
    def event():
        from notifier import trigger_event

        data = request.get_json(silent=True) or {}
        event_type = data.get("event_type", "fall")
        try:
            result = trigger_event(event_type)
        except KeyError as e:
            return jsonify({"error": f"missing env var: {e.args[0]}"}), 500
        return jsonify(result)

    return app
