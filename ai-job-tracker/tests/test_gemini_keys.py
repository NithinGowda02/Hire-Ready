import requests, os
from dotenv import load_dotenv

load_dotenv()

for var in ['GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3']:
    key = os.environ.get(var, 'NOT FOUND')
    if key == 'NOT FOUND':
        print(f'{var}: NOT FOUND in .env')
        continue
    r = requests.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}',
        json={'contents': [{'parts': [{'text': 'Hi'}]}]},
        timeout=30
    )
    data = r.json()
    err = data.get('error', {}).get('message', 'OK')[:100]
    print(f'{var}: Status {r.status_code} | {err}')