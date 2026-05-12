# app/routes/resume.py

import io
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask       import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from app         import db
from app.models.user            import Resume, Profile
from app.services.ai_service    import generate_ats_resume, parse_resume_against_jd, condense_profile_with_ai
from app.services.pdf_generator import generate_pdf_resume
from app.services.resume_parser import parse_resume_file

resume_bp = Blueprint('resume', __name__, url_prefix='/resume')


def _flatten_skill_names(skills) -> list[str]:
    """Normalise skills into a flat list of displayable names."""
    grouped = _build_skills(skills)
    names = []
    for items in grouped.values():
        names.extend(str(item).strip() for item in items if str(item).strip())
    return names


def _is_thin_bullet(text: str) -> bool:
    words = [word for word in str(text).strip().split() if word]
    return len(words) < 8


def _expand_bullets(preferred, fallback, target_count: int = 4) -> list[str]:
    """Prefer rich AI bullets, but fall back to fuller source bullets when needed."""
    chosen = []

    for bullet in preferred or []:
        bullet = str(bullet).strip()
        if bullet and not _is_thin_bullet(bullet):
            chosen.append(bullet)
        if len(chosen) >= target_count:
            return chosen[:target_count]

    for bullet in fallback or []:
        bullet = str(bullet).strip()
        if bullet and bullet not in chosen:
            chosen.append(bullet)
        if len(chosen) >= target_count:
            return chosen[:target_count]

    for bullet in preferred or []:
        bullet = str(bullet).strip()
        if bullet and bullet not in chosen:
            chosen.append(bullet)
        if len(chosen) >= target_count:
            return chosen[:target_count]

    return chosen[:target_count]


def _enrich_condensed_profile(condensed: dict, original: dict) -> dict:
    """Restore detail when the condenser returns overly short bullets."""
    if not isinstance(condensed, dict):
        return original

    enriched = dict(condensed)

    original_exp = original.get('experience') or []
    condensed_exp = []
    for index, exp in enumerate(enriched.get('experience') or []):
        if not isinstance(exp, dict):
            continue
        source = original_exp[index] if index < len(original_exp) and isinstance(original_exp[index], dict) else {}
        item = dict(exp)
        item['bullets'] = _expand_bullets(item.get('bullets'), source.get('bullets'))
        condensed_exp.append(item)
    enriched['experience'] = condensed_exp or original_exp[:3]

    original_projects = original.get('projects') or []
    condensed_projects = []
    for index, project in enumerate(enriched.get('projects') or []):
        if not isinstance(project, dict):
            continue
        source = original_projects[index] if index < len(original_projects) and isinstance(original_projects[index], dict) else {}
        item = dict(project)
        item['bullets'] = _expand_bullets(item.get('bullets'), source.get('bullets'))
        condensed_projects.append(item)
    enriched['projects'] = condensed_projects or original_projects[:3]

    return enriched


# ── Generate resume ───────────────────────────────────────────────────────────
@resume_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        profile = Profile.query.filter_by(user_id=current_user.id).first()

        if not profile:
            return jsonify({'error': 'Please complete your profile first.'}), 400

        # ── Build rich profile_data — pre-process everything before AI call ──
        profile_data = {
            'name':           current_user.name            or '',
            'email':          current_user.email           or '',
            'phone':          profile.phone                or '',
            'location':       profile.location             or '',
            'linkedin':       profile.linkedin_url         or '',
            'github':         profile.github_url           or '',
            'portfolio':      profile.portfolio_url        or '',
            'summary':        profile.professional_summary or '',
            'experience':     _build_experience(profile.work_experience   or []),
            'education':      _build_education(profile.education          or []),
            'skills':         _build_skills(profile.skills                or []),
            'certifications': _build_certifications(profile.certifications or []),
            'projects':       _build_projects(profile.projects            or []),
        }

        try:
            condensed = condense_profile_with_ai(profile_data)
            condensed = _enrich_condensed_profile(condensed, profile_data)
            pdf_bytes = generate_pdf_resume(condensed)

            resume = Resume(
                user_id=current_user.id,
                title=f'Resume — {current_user.name}',
                content_html=pdf_bytes.hex(),
            )
            db.session.add(resume)
            db.session.commit()

            safe_name = (current_user.name or 'resume').replace(' ', '_')
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f'{safe_name}_Resume.pdf'
            )

        except Exception as exc:
            import traceback; traceback.print_exc()
            return jsonify({'error': f'Resume generation failed: {exc}'}), 500

    return render_template('resume/generate.html')


# ── Download saved resume ─────────────────────────────────────────────────────
@resume_bp.route('/download/<int:resume_id>')
@login_required
def download(resume_id):
    resume = Resume.query.filter_by(
        id=resume_id, user_id=current_user.id
    ).first_or_404()

    pdf_bytes = bytes.fromhex(resume.content_html)
    safe_name = (current_user.name or 'resume').replace(' ', '_')
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        download_name=f'{safe_name}_Resume.pdf',
        as_attachment=True,
    )


# ── ATS Analyze ───────────────────────────────────────────────────────────────
@resume_bp.route('/parse', methods=['GET', 'POST'])
@login_required
def parse():
    if request.method == 'POST':
        job_description = request.form.get('job_description', '').strip()

        if not job_description:
            return jsonify({'error': 'Job description is required.'}), 400
        if len(job_description) < 50:
            return jsonify({'error': 'Job description is too short. Please paste the full description.'}), 400

        # ── Build resume text ─────────────────────────────────────────────────
        resume_text = ''
        uploaded = request.files.get('resume_file')
        if uploaded and uploaded.filename:
            try:
                resume_text = parse_resume_file(uploaded, uploaded.filename)
            except Exception:
                resume_text = ''

        if not resume_text:
            profile = Profile.query.filter_by(user_id=current_user.id).first()
            if profile:
                exp_str = ' '.join(
                    f"{e.get('title','')} at {e.get('company','')}. {e.get('description','')}"
                    for e in (profile.work_experience or []) if isinstance(e, dict)
                )
                edu_str = ' '.join(
                    f"{e.get('degree','')} from {e.get('institution','')}"
                    for e in (profile.education or []) if isinstance(e, dict)
                )
                cert_str = ' '.join(
                    c.get('name', '') for c in (profile.certifications or [])
                    if isinstance(c, dict)
                )
                proj_str = ' '.join(
                    f"{p.get('name','')}. {p.get('description','')}"
                    for p in (profile.projects or []) if isinstance(p, dict)
                )
                resume_text = ' '.join(filter(None, [
                    current_user.name,
                    profile.professional_summary or '',
                    ' '.join(_flatten_skill_names(profile.skills or [])),
                    exp_str, edu_str, cert_str, proj_str,
                ])).strip()

        if not resume_text:
            return jsonify({'error': 'No resume data found. Please upload a PDF or complete your profile.'}), 400

        try:
            result = parse_resume_against_jd(resume_text, job_description)
        except RuntimeError as exc:
            return jsonify({'error': str(exc)}), 500
        except ValueError as exc:
            return jsonify({'error': f'AI returned unexpected response: {exc}'}), 502
        except Exception as exc:
            import traceback; traceback.print_exc()
            return jsonify({'error': f'Analysis failed: {exc}'}), 500

        return jsonify(result)

    return render_template('resume/parse.html')


# ══════════════════════════════════════════════════════════════════════════════
#  Profile data builders — convert raw DB JSON into rich structured dicts
#  that the AI can use to write FULL sentences (not truncated fragments)
# ══════════════════════════════════════════════════════════════════════════════

def _build_experience(exp_list: list) -> list:
    """
    Convert raw experience entries into structured dicts with full
    sentence bullets so the AI doesn't truncate them.
    """
    result = []
    for e in exp_list[:3]:
        if not isinstance(e, dict):
            continue

        # Support multiple field name conventions from profile setup
        title    = (e.get('title')    or e.get('role')        or '').strip()
        company  = (e.get('company')  or e.get('organisation') or '').strip()
        start    = (e.get('start_date') or e.get('from') or '').strip()
        end      = (e.get('end_date')   or e.get('to')   or 'Present').strip()
        duration = (e.get('duration') or f"{start} – {end}").strip(' –')
        desc     = (e.get('description') or e.get('responsibilities') or '').strip()

        # Split description into bullet points on sentence boundaries
        bullets = []
        if desc:
            # Try splitting on newlines first, then periods
            lines = [l.strip() for l in desc.replace('\r', '').split('\n') if l.strip()]
            if len(lines) > 1:
                bullets = lines[:4]
            else:
                # Split on periods but keep complete sentences
                sentences = [s.strip() for s in desc.split('.') if len(s.strip()) > 15]
                bullets = [s + '.' for s in sentences[:4]]

        if not bullets:
            bullets = [desc[:120]] if desc else []

        if title or company:
            result.append({
                'title':    title,
                'company':  company,
                'duration': duration,
                'bullets':  bullets,
                # Pass full description too so AI has all context
                'full_description': desc,
            })
    return result


def _build_projects(proj_list: list) -> list:
    """
    Convert raw project entries into structured dicts with full
    sentence bullets preserving all detail.
    """
    result = []
    for p in proj_list[:3]:
        if not isinstance(p, dict):
            continue

        name = (p.get('name') or p.get('title') or '').strip()
        desc = (p.get('description') or p.get('details') or '').strip()

        # Tech stack — support list or string
        tech = p.get('tech_stack') or p.get('technologies') or p.get('tech') or ''
        if isinstance(tech, list):
            tech = ', '.join(str(t) for t in tech)
        tech = str(tech).strip()

        url = (p.get('url') or p.get('link') or '').strip()

        # Split description into bullets
        bullets = []
        if desc:
            lines = [l.strip() for l in desc.replace('\r', '').split('\n') if l.strip()]
            if len(lines) > 1:
                bullets = lines[:4]
            else:
                sentences = [s.strip() for s in desc.split('.') if len(s.strip()) > 15]
                bullets = [s + '.' for s in sentences[:4]]

        if not bullets and desc:
            bullets = [desc[:120]]

        if name:
            result.append({
                'name':             name,
                'tech':             tech,
                'url':              url,
                'bullets':          bullets,
                # Pass full description so AI has all context
                'full_description': desc,
            })
    return result


def _build_skills(skills) -> dict:
    """
    Convert skills (list or dict) into categorised dict.
    Preserves ALL skills — does not drop any.
    """
    if not skills:
        return {}

    # Already a dict with categories
    if isinstance(skills, dict):
        return {k: list(v) for k, v in skills.items()}

    # List of dicts with category + items
    if isinstance(skills, list) and skills and isinstance(skills[0], dict):
        result = {}
        for s in skills:
            cat   = s.get('category', 'Skills')
            items = s.get('items', [])
            if items:
                result[cat] = [str(i) for i in items]
        return result

    # Flat list of strings — try to auto-categorise
    if isinstance(skills, list):
        lang_keywords   = {'python','javascript','typescript','java','c++','c#',
                           'ruby','go','rust','swift','kotlin','php','r','sql',
                           'html','css','bash','scala'}
        frame_keywords  = {'flask','django','react','vue','angular','express',
                           'fastapi','spring','rails','laravel','nextjs','nuxt',
                           'node','nodejs'}
        tool_keywords   = {'git','github','gitlab','docker','kubernetes','aws',
                           'gcp','azure','postgresql','mysql','mongodb','redis',
                           'nginx','linux','postman','figma','jira','render'}

        languages, frameworks, tools, other = [], [], [], []
        for skill in skills:
            s_lower = str(skill).lower().strip()
            if s_lower in lang_keywords:
                languages.append(skill)
            elif s_lower in frame_keywords:
                frameworks.append(skill)
            elif s_lower in tool_keywords:
                tools.append(skill)
            else:
                other.append(skill)

        result = {}
        if languages:  result['Programming Languages'] = languages
        if frameworks: result['Frameworks']            = frameworks
        if tools:      result['Tools']                 = tools
        if other:      result['Other']                 = other
        # If nothing matched categories, put everything under Technical Skills
        if not result:
            result['Technical Skills'] = [str(s) for s in skills]
        return result

    return {}


def _build_certifications(cert_list: list) -> list:
    """Normalise certification entries."""
    result = []
    for c in cert_list:
        if isinstance(c, dict):
            result.append({
                'name':   (c.get('name')   or c.get('title')      or '').strip(),
                'issuer': (c.get('issuer') or c.get('provider')   or '').strip(),
                'date':   (c.get('date')   or c.get('year')
                           or c.get('issued_date')                 or '').strip(),
            })
        elif isinstance(c, str) and c.strip():
            result.append({'name': c.strip(), 'issuer': '', 'date': ''})
    return result[:4]


def _build_education(edu_list: list) -> list:
    """Normalise education entries."""
    result = []
    for e in edu_list:
        if not isinstance(e, dict):
            continue
        result.append({
            'degree':      (e.get('degree')      or e.get('qualification') or '').strip(),
            'institution': (e.get('institution') or e.get('school')
                            or e.get('university')                         or '').strip(),
            'year':        (e.get('year') or e.get('end_date')
                            or e.get('graduation_year')                    or '').strip(),
        })
    return result
