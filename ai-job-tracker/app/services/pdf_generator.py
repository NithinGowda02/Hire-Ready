# app/services/pdf_generator.py
#
# Generates a clean, professional single-page PDF resume using ReportLab.
# Drop-in replacement — same function signature, same return type (bytes).
# resume.py does NOT need any changes.

from io     import BytesIO
from typing import List

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen        import canvas as rl_canvas


# ── page constants ────────────────────────────────────────────────────────────
PW, PH  = letter          # 612 × 792 pt  (8.5 × 11 in)
ML      = 36              # left  margin  (0.50 in)
MR      = 36              # right margin  (0.50 in)
MT      = 38              # top   margin
MB      = 30              # bottom margin
TW      = PW - ML - MR   # usable text width  (540 pt)

# ── typography ────────────────────────────────────────────────────────────────
F_REG   = 'Helvetica'
F_BOLD  = 'Helvetica-Bold'
F_OBL   = 'Helvetica-Oblique'

SZ_NAME = 20     # candidate name
SZ_CONT = 9      # contact line
SZ_HEAD = 10.5   # section heading
SZ_BODY = 10     # normal body text
SZ_BULL = 9.5    # bullet text
SZ_DATE = 9.5    # right-aligned dates / meta

# ── vertical rhythm (points) ──────────────────────────────────────────────────
LH_BODY = 13.5   # line height for body text
LH_BULL = 13     # line height for bullets
GAP_SEC = 10     # space before each new section header
GAP_AFT = 5      # space after section header rule
GAP_ENT = 7      # space between entries within a section
GAP_BUL = 2      # extra space after a bullet block


# ══════════════════════════════════════════════════════════════════════════════
def generate_pdf_resume(profile: dict) -> bytes:
    """
    Build and return a single-page PDF resume as raw bytes.
    Input `profile` is the condensed dict produced by condense_profile_with_ai().
    """
    buf = BytesIO()
    c   = rl_canvas.Canvas(buf, pagesize=letter)

    # shared mutable cursor (list so nested funcs can mutate it)
    cur = [PH - MT]

    # ── primitive helpers ─────────────────────────────────────────────────────

    def sw(text: str, font: str, size: float) -> float:
        """String width in points."""
        return c.stringWidth(str(text), font, size)

    def wordwrap(text: str, font: str, size: float, width: float) -> List[str]:
        """Wrap text to fit within `width` points; return list of lines."""
        words = str(text).split()
        lines, line = [], []
        for w in words:
            probe = ' '.join(line + [w])
            if sw(probe, font, size) <= width:
                line.append(w)
            else:
                if line:
                    lines.append(' '.join(line))
                line = [w]
        if line:
            lines.append(' '.join(line))
        return lines or ['']

    def draw(text: str, x: float, font=F_REG, size=SZ_BODY,
             color=(0, 0, 0)) -> None:
        """Draw text at (x, cur[0]) without advancing the cursor."""
        c.setFont(font, size)
        c.setFillColorRGB(*color)
        c.drawString(x, cur[0], str(text))

    def draw_right(text: str, font=F_REG, size=SZ_DATE) -> None:
        """Draw text right-aligned to the right margin at cur[0]."""
        c.setFont(font, size)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawRightString(PW - MR, cur[0], str(text))

    def draw_center(text: str, font=F_REG, size=SZ_BODY) -> None:
        """Draw text centered on the page at cur[0]."""
        c.setFont(font, size)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(PW / 2, cur[0], str(text))

    def nl(pts: float) -> None:
        """Advance cursor downward by `pts` points."""
        cur[0] -= pts

    def hline(thickness=0.6, color=(0, 0, 0)) -> None:
        """Draw a full-width horizontal rule at cur[0]."""
        c.setLineWidth(thickness)
        c.setStrokeColorRGB(*color)
        c.line(ML, cur[0], PW - MR, cur[0])

    def wrapped_body(text: str, x: float, width: float,
                     font=F_REG, size=SZ_BODY) -> None:
        """Draw wrapped text starting at x, advancing cur per line."""
        for line in wordwrap(text, font, size, width):
            draw(line, x, font, size)
            nl(LH_BODY)

    # ── section heading ───────────────────────────────────────────────────────

    def section(title: str) -> None:
        nl(GAP_SEC)
        draw(title.upper(), ML, F_BOLD, SZ_HEAD)
        nl(14)
        hline(thickness=0.75)
        nl(GAP_AFT + 10)

    # ── bullet point ──────────────────────────────────────────────────────────

    def bullet(text: str) -> None:
        indent = ML + 10
        bwidth = TW - 10
        lines  = wordwrap(text, F_REG, SZ_BULL, bwidth)
        for i, line in enumerate(lines):
            if i == 0:
                draw('\u2022', ML, F_REG, SZ_BULL, color=(0.2, 0.2, 0.2))
            draw(line, indent, F_REG, SZ_BULL)
            nl(LH_BULL)

    # ── entry header row (role left, date right) ──────────────────────────────

    def entry_header(left_bold: str, left_normal: str = '',
                     right: str = '') -> None:
        """
        Draws:  [left_bold  left_normal]            [right]
        left_bold  → Helvetica-Bold  e.g. job title / project name
        left_normal→ Helvetica       e.g. company name
        right      → right-aligned   e.g. date range
        """
        c.setFont(F_BOLD, SZ_BODY)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(ML, cur[0], left_bold)
        if left_normal:
            x_after = ML + sw(left_bold, F_BOLD, SZ_BODY) + 4
            c.setFont(F_OBL, SZ_BODY - 0.5)
            c.setFillColorRGB(0.25, 0.25, 0.25)
            c.drawString(x_after, cur[0], left_normal)
        if right:
            draw_right(right)
        nl(LH_BODY + 1)

    # ══════════════════════════════════════════════════════════════════════════
    #  HEADER — name + contact
    # ══════════════════════════════════════════════════════════════════════════

    name = (profile.get('name') or 'Your Name').strip()
    c.setFont(F_BOLD, SZ_NAME)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(PW / 2, cur[0], name)
    nl(SZ_NAME + 4)

    # contact — row 1: personal details  |  row 2: profile links
    sep = '   \u00b7   '   # narrow middle dot separator

    row1_parts = [
        profile.get('email',    ''),
        profile.get('phone',    ''),
        profile.get('location', ''),
    ]
    row1 = sep.join(p.strip() for p in row1_parts if p.strip())

    def clean_url(u: str) -> str:
        return (u or '').replace('https://', '').replace('http://', '').rstrip('/')

    row2_parts = [
        clean_url(profile.get('linkedin',  '')),
        clean_url(profile.get('github',    '')),
        clean_url(profile.get('portfolio', '')),
    ]
    row2 = sep.join(p for p in row2_parts if p)

    c.setFont(F_REG, SZ_CONT)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    if row1:
        c.drawCentredString(PW / 2, cur[0], row1)
        nl(SZ_CONT + 3)
    if row2:
        c.drawCentredString(PW / 2, cur[0], row2)
        nl(SZ_CONT + 3)

    # thin rule under header — with proper breathing room above and below
    nl(4)
    hline(thickness=1.0)
    nl(20)

    # ══════════════════════════════════════════════════════════════════════════
    #  SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    summary = (profile.get('summary') or '').strip()
    if summary:
        section('Summary')
        wrapped_body(summary, ML, TW)
        nl(GAP_BUL)

    # ══════════════════════════════════════════════════════════════════════════
    #  EXPERIENCE
    # ══════════════════════════════════════════════════════════════════════════

    experience = profile.get('experience') or []
    if experience:
        section('Experience')
        for exp in experience[:3]:
            role     = (exp.get('title',    '') or '').strip()
            company  = (exp.get('company',  '') or '').strip()
            duration = (exp.get('duration', '') or '').strip()
            bullets  = exp.get('bullets',   []) or []

            label = role
            sub   = f'| {company}' if company else ''
            entry_header(label, sub, duration)

            for b in (bullets[:4]):
                if b:
                    bullet(str(b))
            nl(GAP_ENT)

    # ══════════════════════════════════════════════════════════════════════════
    #  PROJECTS
    # ══════════════════════════════════════════════════════════════════════════

    projects = profile.get('projects') or []
    if projects:
        section('Projects')
        for proj in projects[:3]:
            pname   = (proj.get('name',    '') or '').strip()
            tech    = (proj.get('tech',    '') or '').strip()
            pbulls  = proj.get('bullets',  []) or []

            tech_label = f'({tech})' if tech else ''
            entry_header(pname, tech_label)

            for b in (pbulls[:4]):
                if b:
                    bullet(str(b))
            nl(GAP_ENT)

    # ══════════════════════════════════════════════════════════════════════════
    #  TECHNICAL SKILLS
    # ══════════════════════════════════════════════════════════════════════════

    skills = profile.get('skills') or {}
    if skills:
        section('Technical Skills')
        cat_w = 140   # fixed width for category label column

        for category, items in list(skills.items())[:5]:
            items = items or []
            if not items:
                continue

            skill_str = ', '.join(str(s) for s in items[:8])
            avail_w   = TW - cat_w

            # Draw category label (bold) + skill list (normal) on same baseline
            c.setFont(F_BOLD, SZ_BODY)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(ML, cur[0], str(category))

            # wrap skills into avail_w
            skill_lines = wordwrap(skill_str, F_REG, SZ_BODY, avail_w)
            for i, line in enumerate(skill_lines):
                if i > 0:
                    nl(LH_BODY)
                c.setFont(F_REG, SZ_BODY)
                c.setFillColorRGB(0.15, 0.15, 0.15)
                c.drawString(ML + cat_w, cur[0], line)
            nl(LH_BODY + 1)

        nl(GAP_BUL)

    # ══════════════════════════════════════════════════════════════════════════
    #  CERTIFICATIONS
    # ══════════════════════════════════════════════════════════════════════════

    certs = profile.get('certifications') or []
    if certs:
        section('Certifications')
        for cert in certs[:4]:
            cname  = (cert.get('name',   '') or '').strip()
            issuer = (cert.get('issuer', '') or '').strip()
            date_  = (cert.get('date',   '') or '').strip()

            parts = [cname]
            if issuer:
                parts.append(issuer)
            line = '  \u2014  '.join(parts)
            if date_:
                line += f'  ({date_})'

            bullet(line)
        nl(GAP_BUL)

    # ══════════════════════════════════════════════════════════════════════════
    #  EDUCATION
    # ══════════════════════════════════════════════════════════════════════════

    education = profile.get('education') or []
    if education:
        section('Education')
        for edu in education:
            degree  = (edu.get('degree',      '') or '').strip()
            school  = (edu.get('institution', '') or edu.get('school', '') or '').strip()
            year    = (edu.get('year',        '') or '').strip()

            entry_header(degree, f'| {school}' if school else '', year)
            nl(GAP_ENT - 4)

    # ══════════════════════════════════════════════════════════════════════════

    c.save()
    buf.seek(0)
    return buf.getvalue()