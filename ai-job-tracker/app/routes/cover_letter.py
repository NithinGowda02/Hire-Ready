# app/routes/cover_letter.py

from flask       import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.user         import Profile
from app.services.ai_service import generate_cover_letter

cover_letter_bp = Blueprint('cover_letter', __name__, url_prefix='/cover-letter')


@cover_letter_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        job_description = request.form.get('job_description', '').strip()
        company_name    = request.form.get('company_name',    '').strip()

        # ── Validate inputs ────────────────────────────────────
        if not job_description:
            return jsonify({'error': 'Job description is required.'}), 400

        if len(job_description) < 50:
            return jsonify({'error': 'Job description is too short. Please paste the full description.'}), 400

        # ── Load profile ───────────────────────────────────────
        profile = Profile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            return jsonify({'error': 'Please complete your profile first before generating a cover letter.'}), 400

        # ── Build profile dict — safely handle None values ─────
        profile_data = {
            'name':       current_user.name        or '',
            'email':      current_user.email       or '',
            'phone':      profile.phone            or '',
            'location':   profile.location         or '',
            'linkedin':   profile.linkedin_url     or '',
            'github':     profile.github_url       or '',
            'summary':    profile.professional_summary or '',
            'experience': profile.work_experience  or [],
            'education':  profile.education        or [],
            'skills':     profile.skills           or [],
        }

        # ── Generate ───────────────────────────────────────────
        try:
            cover_letter_text = generate_cover_letter(
                profile_data,
                job_description,
                company_name or 'the company'   # fallback so the prompt always has a name
            )
        except Exception as exc:
            # Log full traceback server-side, return safe message to client
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Generation failed: {str(exc)}'}), 500

        if not cover_letter_text or not cover_letter_text.strip():
            return jsonify({'error': 'AI returned an empty response. Please try again.'}), 500

        return jsonify({'cover_letter': cover_letter_text.strip()})

    # GET → render the page
    return render_template('cover_letter/generate.html')