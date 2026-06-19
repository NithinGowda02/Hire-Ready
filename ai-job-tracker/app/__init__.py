from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import DevelopmentConfig, ProductionConfig

import os
import socket
from urllib.parse import urlparse


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()


def create_app():
    app = Flask(__name__)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(DevelopmentConfig if env == 'development' else ProductionConfig)

    db_url = os.environ.get('DATABASE_URL', '')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)

    if db_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url

        engine_options = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }

        # Render's network can't route IPv6, but Neon's hostname sometimes
        # resolves to an AAAA (IPv6) record. Force libpq to dial the IPv4
        # address directly via hostaddr, while keeping the hostname for SSL.
        try:
            hostname = urlparse(db_url).hostname
            if hostname:
                ipv4_addr = socket.gethostbyname(hostname)
                engine_options['connect_args'] = {'hostaddr': ipv4_addr}
        except socket.gaierror:
            # Fall back to normal resolution if IPv4 lookup fails
            pass

        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    oauth.init_app(app)

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

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/privacy')
    def privacy():
        return render_template('legal/privacy.html')

    @app.route('/terms')
    def terms():
        return render_template('legal/terms.html')

    @app.route('/help')
    def help_page():
        return render_template('legal/help.html')

    @app.context_processor
    def inject_template_globals():
        return {'current_year': 2026}

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    return app