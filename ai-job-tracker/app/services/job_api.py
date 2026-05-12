# app/services/job_api.py

import re
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Always resolve .env relative to this file, not the cwd
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / '.env', override=True)


def fetch_jobs(keyword: str, location: str = 'india', page: int = 1, results: int = 20) -> dict:
    """
    Fetch live jobs from Adzuna API.
    Register free at: developer.adzuna.com
    Add to .env:  ADZUNA_APP_ID=...   ADZUNA_APP_KEY=...
    """
    app_id  = os.environ.get('ADZUNA_APP_ID',  '').strip()
    app_key = os.environ.get('ADZUNA_APP_KEY',  '').strip() or \
              os.environ.get('ADZUNA_API_KEY',  '').strip()

    # ── Guard: keys missing ───────────────────────────────────────────────
    if not app_id or not app_key:
        raise RuntimeError(
            "Adzuna API credentials are missing. "
            "Register free at developer.adzuna.com and add "
            "ADZUNA_APP_ID and ADZUNA_APP_KEY to your .env file."
        )

    # Adzuna India endpoint
    url = f"https://api.adzuna.com/v1/api/jobs/in/search/{page}"

    params = {
        'app_id':           app_id,
        'app_key':          app_key,
        'results_per_page': results,
        'what':             keyword,
        'where':            location,
        'content-type':     'application/json',
        'sort_by':          'date',          # newest first
    }

    try:
        response = requests.get(url, params=params, timeout=15)

        # Surface Adzuna error messages clearly
        if response.status_code == 401:
            raise RuntimeError(
                "Adzuna API key is invalid (401). "
                "Check ADZUNA_APP_ID and ADZUNA_APP_KEY in your .env file."
            )
        if response.status_code == 403:
            raise RuntimeError(
                "Adzuna API access forbidden (403). "
                "Your key may not have access to the India endpoint."
            )

        response.raise_for_status()
        data = response.json()

        jobs = []
        for job in data.get('results', []):
            # Salary — Adzuna returns annual figures in local currency
            salary_min = job.get('salary_min')
            salary_max = job.get('salary_max')

            # Description — strip HTML tags Adzuna sometimes includes
            desc_raw   = job.get('description', '') or ''
            desc_clean = re.sub(r'<[^>]+>', '', desc_raw).strip()

            jobs.append({
                'id':          job.get('id', ''),
                'title':       job.get('title', 'Untitled Role'),
                'company':     (job.get('company')  or {}).get('display_name', 'Unknown Company'),
                'location':    (job.get('location') or {}).get('display_name', location.title()),
                'salary_min':  int(salary_min) if salary_min else None,
                'salary_max':  int(salary_max) if salary_max else None,
                'description': desc_clean[:300] + ('…' if len(desc_clean) > 300 else ''),
                'url':         job.get('redirect_url', '#'),
                'created':     job.get('created', ''),
                'category':    (job.get('category') or {}).get('label', ''),
                'job_type':    job.get('contract_time', ''),   # full_time / part_time
            })

        total = int(data.get('count', 0))
        return {
            'jobs':  jobs,
            'total': total,
            'page':  page,
            'pages': max(1, -(-total // results)),  # ceiling division
        }

    except requests.exceptions.Timeout:
        raise RuntimeError("Adzuna request timed out. Please try again.")
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Adzuna API error: {exc}")