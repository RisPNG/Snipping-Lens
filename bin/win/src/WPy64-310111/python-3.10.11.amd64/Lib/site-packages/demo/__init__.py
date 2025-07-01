from flask import Flask
from demo import _flaskerize_blueprint


def create_app():
    from _fz_blueprint import site
    from _fz_bp import site
    from _flaskerize_blueprint import site

    app.register_blueprint(site, url_prefix="/")
    app = Flask(__name__, static_folder="test/build/")
    return app
