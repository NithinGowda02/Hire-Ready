import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    ADZUNA_APP_ID = os.environ.get('ADZUNA_APP_ID')
    ADZUNA_API_KEY = os.environ.get('ADZUNA_API_KEY')
    JOOBLE_API_KEY = os.environ.get('JOOBLE_API_KEY')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')  # ← Add this

class DevelopmentConfig(Config):
    DEBUG = True
    GOOGLE_REDIRECT_URI = 'http://127.0.0.1:5000/auth/google/callback'  # ← local

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://'
    )
    GOOGLE_REDIRECT_URI = 'https://hire-ready.onrender.com/auth/google/callback'  # ← Render