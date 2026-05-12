from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Null for Google OAuth users
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    profile = db.relationship('Profile', backref='user', uselist=False)
    resumes = db.relationship('Resume', backref='user', lazy=True)

class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Personal Info
    phone = db.Column(db.String(20))
    location = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(500))
    github_url = db.Column(db.String(500))
    portfolio_url = db.Column(db.String(500))
    professional_summary = db.Column(db.Text)

    # JSON fields for structured data
    work_experience = db.Column(db.JSON, default=list)  # [{title, company, duration, description}]
    education = db.Column(db.JSON, default=list)        # [{degree, institution, year, gpa}]
    achievements = db.Column(db.JSON, default=list)     # [{title, description, date, category}]
    skills = db.Column(db.JSON, default=list)           # [{category, items}]
    certifications = db.Column(db.JSON, default=list)   # [{name, issuer, year}]
    projects = db.Column(db.JSON, default=list)         # [{name, description, tech_stack, url}]
    languages = db.Column(db.JSON, default=list)        # [{language, proficiency}]

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255))
    content_html = db.Column(db.Text)
    pdf_path = db.Column(db.String(500))
    ats_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)