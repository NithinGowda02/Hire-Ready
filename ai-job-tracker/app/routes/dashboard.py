# app/routes/dashboard.py

from flask       import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.user import Profile, Resume

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    resumes = (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template('dashboard/index.html', profile=profile, resumes=resumes)