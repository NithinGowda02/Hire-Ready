# app/routes/jobs.py

import io
from flask       import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from app.services.job_api import fetch_jobs
from app.services.ai_service import condense_profile_with_ai
from app.services.pdf_generator import generate_pdf_resume

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs_bp.route('/')
@login_required
def listings():
    return render_template('jobs/listings.html')


@jobs_bp.route('/search')
@login_required
def search():
    keyword  = request.args.get('keyword',  'software engineer').strip() or 'software engineer'
    location = request.args.get('location', 'india').strip()             or 'india'
    page     = max(1, int(request.args.get('page', 1)))
    results  = max(1, min(50, int(request.args.get('results', 20))))

    try:
        data = fetch_jobs(keyword, location, page, results)
    except RuntimeError as exc:
        return jsonify({'error': str(exc), 'jobs': [], 'total': 0, 'pages': 1, 'page': page}), 500
    except Exception as exc:
        return jsonify({'error': f'Unexpected error: {exc}', 'jobs': [], 'total': 0, 'pages': 1, 'page': page}), 500

    return jsonify(data)


# ── Generate Resume (JSON endpoint) ────────────────────────────────────────────
@jobs_bp.route('/generate-resume', methods=['POST'])
@login_required
def generate_resume_pdf():
    """
    Accepts profile data as JSON body, generates and returns PDF.
    POST body: {profile_data dictionary with name, email, phone, etc.}
    Returns: PDF file download
    """
    try:
        # Get profile data from request
        profile_data = request.get_json()
        
        if not profile_data or not isinstance(profile_data, dict):
            return jsonify({'error': 'Invalid profile data. Expected JSON object.'}), 400
        
        # Validate required fields
        if not profile_data.get('name'):
            return jsonify({'error': 'Name is required in profile data.'}), 400
        
        # Step 1: Condense profile with AI
        condensed = condense_profile_with_ai(profile_data)
        
        # Step 2: Generate PDF
        pdf_bytes = generate_pdf_resume(condensed)
        
        # Step 3: Return PDF
        name = profile_data.get('name', 'Resume').replace(" ", "_")
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{name}_Resume.pdf'
        )
        
    except ValueError as exc:
        return jsonify({'error': f'JSON parsing error: {exc}'}), 400
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Resume generation failed: {exc}'}), 500
