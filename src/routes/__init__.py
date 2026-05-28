"""
Package-level exports for route blueprints.
Importing `src.routes` will expose the common blueprint objects so callers
can register them easily or use the convenience `register_blueprints` helper.
"""
from .ai_routes import ai_bp
from .root_routes import root_bp
from .helper_routes import helper_bp
from .swagger_routes import swagger_bp

__all__ = [
    "helper_bp",
    "root_bp",
    "ai_bp",
    "swagger_bp",
    "register_blueprints",
]


def register_blueprints(app):
    """Register all route blueprints on the provided Flask app.

    Arguments:
        app: Flask application instance
    """
    app.register_blueprint(root_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(helper_bp)
    app.register_blueprint(swagger_bp)
