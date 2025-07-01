def register_routes(api, app, root="api"):
    from app.widget import register_routes as attach_widget

    # Add routes
    attach_widget(api, app)
