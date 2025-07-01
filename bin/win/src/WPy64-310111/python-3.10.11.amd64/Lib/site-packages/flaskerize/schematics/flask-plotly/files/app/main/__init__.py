def register_routes(app, base: str = "/"):
    from .view import bp

    app.register_blueprint(bp, url_prefix=base)
