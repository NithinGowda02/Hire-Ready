# app/routes/auth.py

from flask             import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login       import current_user, login_required, login_user, logout_user
from itsdangerous      import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app               import db, oauth
from app.models.user   import User
from app.services.email_service import send_password_reset_email

import os
import re
from typing import Optional


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


def _get_reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


def _generate_reset_token(user: User) -> str:
    return _get_reset_serializer().dumps(
        {
            'user_id':       user.id,
            'password_hash': user.password_hash or '',
        },
        salt='password-reset',
    )


def _verify_reset_token(token: str) -> Optional[User]:
    try:
        data = _get_reset_serializer().loads(
            token,
            salt='password-reset',
            max_age=current_app.config['RESET_PASSWORD_TOKEN_MAX_AGE'],
        )
    except (BadSignature, SignatureExpired):
        return None

    user = User.query.get(data.get('user_id'))
    if not user:
        return None

    # Token is invalidated if password was already changed
    if (user.password_hash or '') != data.get('password_hash', ''):
        return None

    return user


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


# ── Forgot Password ───────────────────────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user  = User.query.filter_by(email=email).first()

        if user:
            try:
                reset_link      = url_for('auth.reset_password', token=_generate_reset_token(user), _external=True)
                expires_minutes = max(current_app.config['RESET_PASSWORD_TOKEN_MAX_AGE'] // 60, 1)
                send_password_reset_email(user.name, user.email, reset_link, expires_minutes)
            except Exception:
                current_app.logger.exception('Failed to send password reset email to %s', email)

        # Always show the same message — prevents email enumeration attacks
        flash(
            'If an account with that email exists, password reset instructions have been sent.',
            'success',
        )
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


# ── Reset Password ────────────────────────────────────────────────────────────
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    user = _verify_reset_token(token)
    if not user:
        flash('This password reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password         = request.form.get('password',         '')
        confirm_password = request.form.get('confirm_password', '')

        if not password or not confirm_password:
            flash('Both password fields are required.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if not _is_strong_password(password):
            flash(PASSWORD_RULES_MESSAGE, 'error')
            return redirect(url_for('auth.reset_password', token=token))

        user.password_hash = generate_password_hash(password)
        db.session.commit()

        flash('Your password has been reset. You can sign in now.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


# ── Google OAuth — initiate ───────────────────────────────────────────────────
@auth_bp.route('/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    print(f'[OAuth] Redirect URI being sent to Google: {redirect_uri}')
    return google.authorize_redirect(redirect_uri)


# ── Google OAuth — callback ───────────────────────────────────────────────────
@auth_bp.route('/google/callback')
def google_callback():
    try:
        token     = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            raise ValueError('No user info returned from Google')

    except Exception as exc:
        print(f'[OAuth] Google sign-in error: {exc}')
        flash('Google sign-in failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(google_id=user_info['sub']).first()

    if not user:
        user = User.query.filter_by(email=user_info['email']).first()
        if user:
            # Existing email account — link Google ID
            user.google_id  = user_info['sub']
            user.avatar_url = user_info.get('picture') or user.avatar_url
        else:
            # Brand new user via Google
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