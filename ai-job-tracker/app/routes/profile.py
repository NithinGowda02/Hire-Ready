# app/routes/profile.py

import json
import traceback
from sqlalchemy.orm.attributes import flag_modified
from flask       import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app         import db
from app.models.user import Profile

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


def _parse_json_field(form, key):
    """Safely parse a JSON hidden-field from the form.
    Handles: JSON string, already-decoded list/dict, None, and empty string.
    Always returns a list (never None).
    """
    raw = form.get(key, '[]')
    if not raw or raw.strip() == '':
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


@profile_bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    profile = Profile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        # Guard: reject base64 payloads early with a clear message
        avatar_raw = request.form.get('avatar_url', '')
        if avatar_raw.strip().startswith('data:'):
            flash('Please use a hosted image URL instead of uploading a file directly.', 'error')
            return redirect(url_for('profile.setup'))

        try:
            if not profile:
                profile = Profile(user_id=current_user.id)
                db.session.add(profile)

            # Scalar fields
            profile.phone                = request.form.get('phone',                '').strip() or None
            profile.location             = request.form.get('location',             '').strip() or None
            profile.linkedin_url         = request.form.get('linkedin_url',         '').strip() or None
            profile.github_url           = request.form.get('github_url',           '').strip() or None
            profile.portfolio_url        = request.form.get('portfolio_url',        '').strip() or None
            profile.professional_summary = request.form.get('professional_summary', '').strip() or None

            avatar_url = avatar_raw.strip() or None
            current_user.avatar_url = avatar_url

            # JSON fields
            profile.work_experience  = _parse_json_field(request.form, 'work_experience')
            profile.education        = _parse_json_field(request.form, 'education')
            profile.achievements     = _parse_json_field(request.form, 'achievements')
            profile.skills           = _parse_json_field(request.form, 'skills')
            profile.certifications   = _parse_json_field(request.form, 'certifications')
            profile.projects         = _parse_json_field(request.form, 'projects')
            profile.languages        = _parse_json_field(request.form, 'languages')

            for field in ('work_experience', 'education', 'achievements', 'skills',
                          'certifications', 'projects', 'languages'):
                flag_modified(profile, field)

            db.session.commit()
            flash('Profile saved successfully!', 'success')
            return redirect(url_for('dashboard.index'))

        except Exception as e:
            db.session.rollback()
            print(f"[profile.setup] Error:\n{traceback.format_exc()}")
            flash(f'Error saving profile: {e}', 'error')
            return redirect(url_for('profile.setup'))

    return render_template('profile/setup.html', profile=profile)