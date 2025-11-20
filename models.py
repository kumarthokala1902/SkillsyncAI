from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    skills = db.Column(db.Text, nullable=False)
    goals = db.Column(db.Text, nullable=False)
    bio = db.Column(db.Text, default='')
    is_mentor = db.Column(db.Boolean, default=False)
    availability = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    skill_progress = db.relationship('SkillProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # Sessions where user is a mentor
    sessions_mentoring = db.relationship('MentorSession', 
                                       foreign_keys='MentorSession.mentor_id', 
                                       backref='mentor', 
                                       lazy=True)
    
    # Sessions where user is a learner
    sessions_learning = db.relationship('MentorSession', 
                                      foreign_keys='MentorSession.learner_id', 
                                      backref='learner', 
                                      lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_skills_list(self):
        return [s.strip() for s in self.skills.split(',') if s.strip()]
    
    def get_goals_list(self):
        return [g.strip() for g in self.goals.split(',') if g.strip()]
    
    def __repr__(self):
        return f'<User {self.name} ({self.email})>'

class SkillProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def update_progress(self, increment=0.1):
        self.level = min(1.0, self.level + increment)
        self.last_updated = datetime.utcnow()
    
    def __repr__(self):
        return f'<SkillProgress {self.skill_name}: {self.level}>'

class MentorSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    learner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    topic = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    meet_link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text, default='')
    feedback = db.Column(db.Text, default='')
    
    def __repr__(self):
        return f'<MentorSession {self.topic} ({self.status})>'