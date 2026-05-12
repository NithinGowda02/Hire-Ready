# app/routes/auth.py

from flask             import Blueprint, render_template, redirect, url_for, request, flash
from flask_login       import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app               import db, oauth
from app.models.user   import User
import os
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

PASSWORD_RULES_MESSAGE = (
    'Password must be at least 8 characters and include an uppercase letter, '
    'a lowercase letter, a number, and a special character.'
)


def _is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8
        and bool(re.search(r'[A-Z]', password))
        and bool(re.search(r'[a-z]', password))
        and bool(re.search(r'\d', password))
        and bool(re.search(r'[^A-Za-z0-9]', password))
    )

# ── OAuth client ──────────────────────────────────────────────────────────────
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)


# ── Register ──────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name     = request.form.get('name',     '').strip()
        email    = request.form.get('email',    '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.register'))

        if not _is_strong_password(password):
            flash(PASSWORD_RULES_MESSAGE, 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return redirect(url_for('auth.register'))

        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password),
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created! Let's set up your profile.", 'success')
        return redirect(url_for('profile.setup'))

    return render_template('auth/register.html')


# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email    = request.form.get('email',    '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))

        flash('Invalid email or password.', 'error')

    return render_template('auth/login.html')


# ── Google OAuth — initiate ───────────────────────────────────────────────────
@auth_bp.route('/google')
def google_login():
    # Build redirect URI from environment so it works in both local and production
    base_url = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5000').rstrip('/')
    redirect_uri = f"{base_url}/auth/google/callback"

    print(f"[OAuth] Redirect URI being sent to Google: {redirect_uri}")  # debug log

    return google.authorize_redirect(redirect_uri)


# ── Google OAuth — callback ───────────────────────────────────────────────────
@auth_bp.route('/google/callback')
def google_callback():
    # Must use same URI as in google_login
    base_url = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5000').rstrip('/')
    redirect_uri = f"{base_url}/auth/google/callback"

    try:
        token     = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            raise ValueError("No user info returned from Google")

    except Exception as e:
        print(f"[OAuth] Google sign-in error: {e}")
        flash('Google sign-in failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    # Find or create user
    user = User.query.filter_by(google_id=user_info['sub']).first()

    if not user:
        user = User.query.filter_by(email=user_info['email']).first()
        if user:
            user.google_id  = user_info['sub']
            user.avatar_url = user_info.get('picture') or user.avatar_url
        else:
            user = User(
                email=user_info['email'],
                name=user_info['name'],
                google_id=user_info['sub'],
                avatar_url=user_info.get('picture'),
                is_verified=True,
            )
            db.session.add(user)

    db.session.commit()
    login_user(user)

    if not user.profile:
        flash('Welcome! Please complete your profile to get started.', 'success')
        return redirect(url_for('profile.setup'))

    return redirect(url_for('dashboard.index'))


# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You've been signed out.", 'success')
    return redirect(url_for('home'))
