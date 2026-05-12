# 🚀 AI-Powered Job Tracker Application

> **Tech Stack:** Python · Flask · PostgreSQL · HTML · CSS · JavaScript · Google OAuth · Google Gemini API (Free Tier) · Jooble/Adzuna Job API

An intelligent job search platform that uses AI to help users create ATS-optimized resumes, analyze job matches, and generate personalized cover letters.

## ✨ Features

- **AI-Powered Resume Generation** - Create ATS-friendly resumes using Google Gemini
- **Resume ATS Analysis** - Get detailed match scores against job descriptions
- **Smart Cover Letters** - Generate personalized cover letters for specific roles
- **Job Search Integration** - Search jobs from Adzuna API
- **Google OAuth Authentication** - Secure login with Google accounts
- **Profile Management** - Comprehensive user profile with work experience, skills, etc.
- **PDF Export** - Download resumes as professional PDF documents

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL
- Google Cloud account (for Gemini API and OAuth)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-job-tracker
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**
   ```sql
   CREATE DATABASE job_tracker_db;
   CREATE USER job_tracker_user WITH PASSWORD 'yourpassword';
   GRANT ALL PRIVILEGES ON DATABASE job_tracker_db TO job_tracker_user;
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database URL
   ```

6. **Run database migrations**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

7. **Start the application**
   ```bash
   python run.py
   ```

## 🔑 API Keys Setup

### Google Gemini API (Free Tier)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env`: `GOOGLE_API_KEY=your_api_key`

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API and Google Identity API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback` (development)
   - `https://yourdomain.com/auth/google/callback` (production)
6. Add to `.env`:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

### Job APIs (Optional)
- **Adzuna API**: Get API key from [developer.adzuna.com](https://developer.adzuna.com/)
- **Jooble API**: Get API key from their website

## 🚀 Usage

1. **Register/Login** with Google OAuth
2. **Complete your profile** with work experience, skills, education
3. **Generate AI-powered resumes** optimized for ATS systems
4. **Analyze resume match** against job descriptions
5. **Create personalized cover letters** for specific positions
6. **Search and track jobs** from integrated job boards

## 📁 Project Structure

```
ai-job-tracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # Database models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── dashboard.py     # Dashboard routes
│   │   ├── profile.py       # Profile management
│   │   ├── resume.py        # Resume operations
│   │   ├── cover_letter.py  # Cover letter generation
│   │   └── jobs.py          # Job search
│   ├── services/
│   │   ├── ai_service.py    # Google Gemini integration
│   │   ├── job_api.py       # Job API integration
│   │   ├── pdf_generator.py # PDF generation
│   │   └── resume_parser.py # Resume parsing
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css    # Main styles
│   │   │   └── components.css
│   │   └── js/
│   │       ├── main.js      # Main JavaScript
│   │       ├── dashboard.js
│   │       ├── resume.js
│   │       └── charts.js
│   └── templates/           # Jinja2 templates
│       ├── base.html
│       ├── home.html
│       ├── auth/
│       ├── dashboard/
│       ├── profile/
│       ├── resume/
│       ├── cover_letter/
│       └── jobs/
├── migrations/              # Database migrations
├── tests/                   # Test files
├── .env                     # Environment variables
├── .env.example            # Environment template
├── requirements.txt         # Python dependencies
├── run.py                  # Application entry point
└── README.md
```

## 🔧 Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Formatting
```bash
black .
flake8 .
```

### Database Operations
```bash
# Create migration
flask db migrate -m "Migration message"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

## 🚢 Deployment

### Render.com Deployment
1. Connect your GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn run:app`
4. Add environment variables in Render dashboard
5. Deploy!

### Environment Variables for Production
```
FLASK_ENV=production
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
GOOGLE_API_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini for AI capabilities
- Adzuna for job data
- Flask community for the excellent framework
- All contributors and users

---

**Made with ❤️ for job seekers worldwide**