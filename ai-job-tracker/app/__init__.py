from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from app.config import DevelopmentConfig, ProductionConfig
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()

def create_app():
    app = Flask(__name__)

    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(DevelopmentConfig if env == 'development' else ProductionConfig)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    oauth.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.profile import profile_bp
    from app.routes.resume import resume_bp
    from app.routes.cover_letter import cover_letter_bp
    from app.routes.jobs import jobs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(cover_letter_bp)
    app.register_blueprint(jobs_bp)

    # Home route
    @app.route('/')
    def home():
        return render_template('home.html')

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    return app