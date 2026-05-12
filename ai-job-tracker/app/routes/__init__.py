# app/routes/__init__.py
# Registers all blueprints with the Flask app

from app.routes.auth         import auth_bp
from app.routes.dashboard    import dashboard_bp
from app.routes.profile      import profile_bp
from app.routes.resume       import resume_bp
from app.routes.jobs         import jobs_bp
from app.routes.cover_letter import cover_letter_bp


def register_blueprints(app):
    """Register every blueprint. Called from app factory (create_app)."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(cover_letter_bp)