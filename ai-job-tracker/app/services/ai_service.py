# app/services/ai_service.py
#
# Tries providers in this order — automatically, no manual switching needed:
#   1. Groq         → console.groq.com       (free, resets every hour)
#   2. OpenRouter   → openrouter.ai/keys     (free, resets every day)
#   3. Gemini       → aistudio.google.com    (free, resets every day)
#
# Add whichever keys you have to .env — the more keys, the more reliable.
# You do NOT need all three — even one key is enough to run the app.

import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env', override=True)


# ── provider endpoints & model lists ──────────────────────────────────────

GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

OPENROUTER_URL    = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
]

GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


# ══════════════════════════════════════════════════════════════════════════
#  Provider functions — each returns text on success, None if key missing,
#  raises RuntimeError only on unrecoverable errors (bad key, etc.)
# ══════════════════════════════════════════════════════════════════════════

def _try_groq(prompt: str, max_tokens: int) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    for model in GROQ_MODELS:
        for attempt in range(3):
            try:
                resp = requests.post(
                    GROQ_URL,
                    headers=headers,
                    json={
                        "model":      model,
                        "max_tokens": max_tokens,
                        "messages":   [{"role": "user", "content": prompt}],
                    },
                    timeout=60,
                )

                if resp.status_code == 401:
                    print("[ai] Groq: invalid API key, skipping.")
                    return None

                if resp.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"[ai] Groq 429 on {model}, waiting {wait}s …")
                    time.sleep(wait)
                    continue

                if resp.status_code in (404, 503):
                    print(f"[ai] Groq {resp.status_code} on {model}, trying next model …")
                    break

                resp.raise_for_status()

                choices = resp.json().get("choices") or []
                text = (choices[0].get("message") or {}).get("content", "").strip() if choices else ""
                if not text:
                    break

                print(f"[ai] ✓ Groq / {model}")
                return text

            except requests.exceptions.Timeout:
                if attempt == 2:
                    break
                time.sleep(5)
            except Exception as exc:
                print(f"[ai] Groq error on {model}: {exc}")
                break

    return None


def _try_openrouter(prompt: str, max_tokens: int) -> str | None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "http://localhost:5000",
        "X-Title":       "HireReady",
    }

    for model in OPENROUTER_MODELS:
        for attempt in range(3):
            try:
                resp = requests.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json={
                        "model":      model,
                        "max_tokens": max_tokens,
                        "messages":   [{"role": "user", "content": prompt}],
                    },
                    timeout=90,
                )

                if resp.status_code == 401:
                    print("[ai] OpenRouter: invalid API key, skipping.")
                    return None

                if resp.status_code == 402:
                    print("[ai] OpenRouter: credits exhausted, skipping.")
                    return None

                if resp.status_code == 429:
                    wait = 30 * (attempt + 1)
                    print(f"[ai] OpenRouter 429 on {model}, waiting {wait}s …")
                    time.sleep(wait)
                    continue

                if resp.status_code in (404, 503):
                    print(f"[ai] OpenRouter {resp.status_code} on {model}, trying next …")
                    break

                resp.raise_for_status()

                choices = resp.json().get("choices") or []
                text = (choices[0].get("message") or {}).get("content", "").strip() if choices else ""
                if not text:
                    break

                print(f"[ai] ✓ OpenRouter / {model}")
                return text

            except requests.exceptions.Timeout:
                if attempt == 2:
                    break
                time.sleep(5)
            except Exception as exc:
                print(f"[ai] OpenRouter error on {model}: {exc}")
                break

    return None


def _try_gemini(prompt: str, max_tokens: int) -> str | None:
    # Support multiple Gemini keys — add as GEMINI_API_KEY_1, _2, _3 etc.
    # Also accepts the plain GEMINI_API_KEY for single-key setups.
    keys = []
    for var in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
        k = os.environ.get(var, "").strip()
        if k and k not in keys:
            keys.append(k)

    if not keys:
        return None

    for api_key in keys:
        for model in GEMINI_MODELS:
            for attempt in range(3):
                try:
                    url = GEMINI_URL.format(model=model, key=api_key)
                    resp = requests.post(
                        url,
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"maxOutputTokens": max_tokens},
                        },
                        timeout=60,
                    )

                    # quota hit — try next key immediately
                    if resp.status_code == 429:
                        print(f"[ai] Gemini 429 on {model} (key …{api_key[-6:]}), trying next key/model …")
                        break

                    if resp.status_code == 400:
                        print(f"[ai] Gemini 400 on {model}, trying next model …")
                        break

                    resp.raise_for_status()

                    data  = resp.json()
                    parts = (
                        ((data.get("candidates") or [{}])[0])
                        .get("content", {})
                        .get("parts", [])
                    )
                    text = "".join(p.get("text", "") for p in parts).strip()
                    if not text:
                        break

                    print(f"[ai] ✓ Gemini / {model}")
                    return text

                except requests.exceptions.Timeout:
                    if attempt == 2:
                        break
                    time.sleep(5)
                except Exception as exc:
                    print(f"[ai] Gemini error on {model}: {exc}")
                    break

    return None


# ══════════════════════════════════════════════════════════════════════════
#  Main entry point
# ══════════════════════════════════════════════════════════════════════════

def _call_ai(prompt: str, max_tokens: int = 2048) -> str:
    """
    Tries Groq → OpenRouter → Gemini in order.
    Returns the first successful response.
    Raises RuntimeError with a helpful message if all providers fail.
    """

    result = _try_groq(prompt, max_tokens)
    if result:
        return result

    print("[ai] Groq unavailable, trying OpenRouter …")
    result = _try_openrouter(prompt, max_tokens)
    if result:
        return result

    print("[ai] OpenRouter unavailable, trying Gemini …")
    result = _try_gemini(prompt, max_tokens)
    if result:
        return result

    raise RuntimeError(
        "All AI providers failed or have no API keys configured.\n\n"
        "Add at least ONE of these to your .env file:\n"
        "  GROQ_API_KEY        → https://console.groq.com      (free, resets hourly)\n"
        "  OPENROUTER_API_KEY  → https://openrouter.ai/keys    (free, resets daily)\n"
        "  GEMINI_API_KEY      → https://aistudio.google.com   (free, resets daily)\n"
    )


# ── helpers ────────────────────────────────────────────────────────────────

def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    m = re.search(r"```(?:\w+)?\s*\n?([\s\S]+?)\n?```", raw)
    return m.group(1).strip() if m else raw


def _strip_markdown(text: str) -> str:
    text = re.sub(r'(?m)^#{1,3}\s+', '', text)
    text = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _flatten_skill_names(skills) -> list[str]:
    """Normalise skills from flat lists, category dicts, or {category, items} rows."""
    if not skills:
        return []

    if isinstance(skills, dict):
        values = []
        for items in skills.values():
            if isinstance(items, list):
                values.extend(str(item).strip() for item in items if str(item).strip())
        return values

    if isinstance(skills, list):
        values = []
        for item in skills:
            if isinstance(item, str) and item.strip():
                values.append(item.strip())
            elif isinstance(item, dict):
                nested = item.get("items", [])
                if isinstance(nested, list):
                    values.extend(str(skill).strip() for skill in nested if str(skill).strip())
        return values

    return []


def _safe_json(raw: str) -> dict:
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r'\{[\s\S]+\}', cleaned)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"AI returned non-JSON:\n{cleaned[:400]}")


# ══════════════════════════════════════════════════════════════════════════
#  Feature 1 — ATS Resume
# ══════════════════════════════════════════════════════════════════════════

def generate_ats_resume(profile_data: dict) -> str:
    prompt = f"""
You are an expert ATS resume writer. Create a clean, ATS-friendly HTML resume
based on this profile data. Use inline CSS only. Standard section headings.

Profile Data:
{json.dumps(profile_data, indent=2)}

Requirements:
- Use <h1> for name, <h2> for sections
- Include: Summary, Experience, Education, Skills, Projects, Certifications
- Return ONLY valid HTML, no markdown fences, no explanation
"""
    raw = _call_ai(prompt, max_tokens=4096)
    return _strip_fences(raw)


# ══════════════════════════════════════════════════════════════════════════
#  Feature 2 — ATS Scorer
# ══════════════════════════════════════════════════════════════════════════

def parse_resume_against_jd(resume_text: str, job_description: str) -> dict:
    prompt = f"""
You are an ATS expert. Analyze this resume against the job description.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return ONLY a valid JSON object — no markdown fences, no extra text:
{{
    "match_percentage": <0-100 integer>,
    "overall_feedback": "<2-3 sentence summary>",
    "section_scores": {{
        "skills":         <0-100>,
        "experience":     <0-100>,
        "education":      <0-100>,
        "certifications": <0-100>
    }},
    "matched_keywords": ["keyword1", "keyword2"],
    "missing_keywords": ["keyword1", "keyword2"],
    "strengths": ["strength1", "strength2"],
    "improvements": [
        {{"priority": "high",   "suggestion": "...", "reason": "..."}},
        {{"priority": "medium", "suggestion": "...", "reason": "..."}},
        {{"priority": "low",    "suggestion": "...", "reason": "..."}}
    ]
}}
"""
    result = _safe_json(_call_ai(prompt, max_tokens=2048))

    result["match_percentage"] = int(result.get("match_percentage", 0))
    result["overall_feedback"] = str(result.get("overall_feedback", ""))
    result["matched_keywords"] = list(result.get("matched_keywords", []))
    result["missing_keywords"] = list(result.get("missing_keywords", []))
    result["strengths"]        = list(result.get("strengths", []))

    raw_ss = result.get("section_scores", {})
    result["section_scores"] = {
        "skills":         int(raw_ss.get("skills",         0)),
        "experience":     int(raw_ss.get("experience",     0)),
        "education":      int(raw_ss.get("education",      0)),
        "certifications": int(raw_ss.get("certifications") or raw_ss.get("keywords", 0)),
    }
    result["improvements"] = [
        {
            "priority":   i.get("priority",   "low"),
            "suggestion": i.get("suggestion", ""),
            "reason":     i.get("reason",     ""),
        }
        for i in result.get("improvements", []) if isinstance(i, dict)
    ]
    return result


# ══════════════════════════════════════════════════════════════════════════
#  Feature 3 — Cover Letter
# ══════════════════════════════════════════════════════════════════════════

def generate_cover_letter(
    profile_data: dict,
    job_description: str,
    company_name: str,
) -> str:
    exp_lines = []
    for exp in (profile_data.get("experience") or []):
        title    = exp.get("title",    "").strip()
        company  = exp.get("company",  "").strip()
        duration = exp.get("duration", "").strip()
        if title or company:
            line = f"  - {title} at {company}"
            if duration:
                line += f" ({duration})"
            exp_lines.append(line)

    experience_str = "\n".join(exp_lines) or "  - Not provided"
    skills_str     = ", ".join(_flatten_skill_names(profile_data.get("skills"))) or "Not provided"

    prompt = f"""
You are a professional career coach and expert cover letter writer.
Write a compelling, personalized cover letter strictly following the structure below.

=== APPLICANT ===
Name:       {profile_data.get('name', '')}
Location:   {profile_data.get('location', '')}
Email:      {profile_data.get('email', '')}
Summary:    {profile_data.get('summary', '')}
Skills:     {skills_str}
Experience:
{experience_str}

=== TARGET ROLE ===
Company:    {company_name}
Job Description:
{job_description}

=== STRICT OUTPUT FORMAT ===
Write the letter in this exact structure — plain text only, no markdown, no subject line:

[Opening line — one strong sentence naming the role with genuine enthusiasm.
NEVER start with "I am writing to apply for" or "I am excited to apply".]

[Paragraph 1 — 2-3 sentences: What draws the applicant specifically to {company_name}.]

[Paragraph 2 — 3-4 sentences: Highlight 2-3 specific skills or achievements matching the JD.]

[Paragraph 3 — 2 sentences: What the applicant brings to the team.]

[Closing — 2 sentences: Thank the reader, clear call to action.]

Sincerely,
{profile_data.get('name', '')}

=== RULES ===
- Output ONLY the letter text. Nothing before or after.
- No markdown, no bullet points, no subject line.
- No filler phrases: "I believe", "I feel", "passionate about".
- Each paragraph separated by a single blank line.
- Total length: 250-350 words.
"""
    raw   = _call_ai(prompt, max_tokens=1024)
    clean = _strip_fences(raw)
    clean = _strip_markdown(clean)

    if not clean:
        raise RuntimeError("Cover letter generation returned empty content. Please try again.")
    return clean


# ══════════════════════════════════════════════════════════════════════════
#  Feature 4 — Profile Condenser
# ══════════════════════════════════════════════════════════════════════════

def condense_profile_with_ai(profile_data: dict) -> dict:
    prompt = f"""
You are an expert resume writer. Rewrite this profile into a strong, content-rich resume draft.
Return ONLY valid JSON — no markdown fences, no explanation.

Profile Data:
{json.dumps(profile_data, indent=2)}

Rules:
- Preserve substance. Do not make the resume feel empty or skeletal.
- Summary: 2-3 sentences, around 45-75 words total
- Experience: max 3 items, exactly 4 bullet points each when enough detail exists
- Projects: max 3 items, exactly 4 bullet points each when enough detail exists
- Each experience/project bullet should be 10-18 words, concrete, and resume-ready
- Prefer achievements, impact, ownership, tools, and outcomes over vague fragments
- Never return bullets with only 4-6 words unless the source material is extremely limited
- Skills: keep the most relevant skills, but preserve meaningful breadth
- Certifications: max 3 total
- Education: all entries

Return this exact JSON structure:
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "1234567890",
    "location": "City, State",
    "linkedin": "linkedin.com/in/username",
    "github": "github.com/username",
    "portfolio": "portfolio.com",
    "summary": "2-sentence professional summary",
    "experience": [
        {{
            "title": "Job Title",
            "company": "Company Name",
            "duration": "Month Year – Month Year",
            "bullets": [
                "Achievement-focused bullet with concrete work, tools, and impact.",
                "Achievement-focused bullet with concrete work, tools, and impact.",
                "Achievement-focused bullet with concrete work, tools, and impact.",
                "Achievement-focused bullet with concrete work, tools, and impact."
            ]
        }}
    ],
    "projects": [
        {{
            "name": "Project Name",
            "tech": "Tech1, Tech2",
            "bullets": [
                "Project bullet describing implementation details, technologies, and measurable outcome.",
                "Project bullet describing implementation details, technologies, and measurable outcome.",
                "Project bullet describing implementation details, technologies, and measurable outcome.",
                "Project bullet describing implementation details, technologies, and measurable outcome."
            ]
        }}
    ],
    "skills": {{
        "Programming Languages": ["Python", "JavaScript"],
        "Frameworks": ["React", "Flask"],
        "Tools": ["Git", "Docker"]
    }},
    "certifications": [
        {{"name": "Cert Name", "issuer": "Issuer", "date": "2024"}}
    ],
    "education": [
        {{
            "degree": "Bachelor of Science",
            "institution": "University Name",
            "year": "2020"
        }}
    ]
}}
"""
    return _safe_json(_call_ai(prompt, max_tokens=3000))
