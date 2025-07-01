from flask import Flask, request, jsonify

from .config import config_by_name


def create_app(config_name: str = "test"):
    """Create Flask App."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Register BluePrints
    from .main import register_routes

    register_routes(app)

    # Add a default root route.
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
