from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, SkillProgress, MentorSession
from ai_engine import SkillMatcher
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skillsync.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

matcher = SkillMatcher()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        skills = request.form.get('skills')
        goals = request.form.get('goals')
        is_mentor = request.form.get('is_mentor') == 'on'
        bio = request.form.get('bio', '')
        availability = request.form.get('availability', '')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('register'))
        
        user = User(
            name=name,
            email=email,
            skills=skills,
            goals=goals,
            is_mentor=is_mentor,
            bio=bio,
            availability=availability
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        for skill in user.get_skills_list():
            progress = SkillProgress(user_id=user.id, skill_name=skill, level=0.2)
            db.session.add(progress)
        db.session.commit()
        
        login_user(user)
        flash(f'Welcome to SkillSync, {name}! 👋', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.name}! 🔥', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    all_users = User.query.all()
    
    if current_user.is_mentor:
        matches = matcher.find_matches(current_user, all_users, top_n=6)
        match_type = 'learners'
    else:
        matches = matcher.find_matches(current_user, all_users, top_n=6)
        match_type = 'mentors'
    
    skill_progress = SkillProgress.query.filter_by(user_id=current_user.id).all()
    
    upcoming_sessions = MentorSession.query.filter(
        (MentorSession.learner_id == current_user.id) | (MentorSession.mentor_id == current_user.id),
        MentorSession.status == 'scheduled'
    ).order_by(MentorSession.scheduled_time).limit(5).all()
    
    return render_template('dashboard.html', 
                         matches=matches, 
                         match_type=match_type,
                         skill_progress=skill_progress,
                         upcoming_sessions=upcoming_sessions)

@app.route('/mentor/<int:mentor_id>')
@login_required
def mentor_profile(mentor_id):
    mentor = User.query.get_or_404(mentor_id)
    return render_template('mentor.html', mentor=mentor)

@app.route('/book-session/<int:mentor_id>', methods=['POST'])
@login_required
def book_session(mentor_id):
    mentor = User.query.get_or_404(mentor_id)
    
    scheduled_time_str = request.form.get('scheduled_time')
    topic = request.form.get('topic', '')
    duration = int(request.form.get('duration', 30))
    
    if not scheduled_time_str or not topic:
        flash('Please provide all required fields.', 'error')
        return redirect(url_for('mentor_profile', mentor_id=mentor_id))
    
    scheduled_time = datetime.fromisoformat(scheduled_time_str)
    
    session = MentorSession(
        mentor_id=mentor_id,
        learner_id=current_user.id,
        scheduled_time=scheduled_time,
        duration_minutes=duration,
        topic=topic,
        status='scheduled'
    )
    
    db.session.add(session)
    db.session.commit()
    
    flash(f'Session booked with {mentor.name}! 🎉', 'success')
    return redirect(url_for('dashboard'))

@app.route('/progress')
@login_required
def progress():
    skill_progress = SkillProgress.query.filter_by(user_id=current_user.id).order_by(SkillProgress.skill_name).all()
    return render_template('progress.html', skill_progress=skill_progress)

@app.route('/api/progress-data')
@login_required
def progress_data():
    skill_progress = SkillProgress.query.filter_by(user_id=current_user.id).order_by(SkillProgress.skill_name).all()
    
    data = {
        'labels': [sp.skill_name for sp in skill_progress],
        'values': [sp.level * 100 for sp in skill_progress]
    }
    return jsonify(data)

@app.route('/update-progress/<int:skill_id>', methods=['POST'])
@login_required
def update_progress(skill_id):
    skill = SkillProgress.query.get_or_404(skill_id)
    
    if skill.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    skill.update_progress(0.1)
    db.session.commit()
    
    return jsonify({'success': True, 'new_level': skill.level * 100})

def init_sample_data():
    if User.query.count() > 0:
        return
    
    mentors_data = [
        {
            'name': 'Sarah Chen',
            'email': 'sarah@skillsync.com',
            'password': 'mentor123',
            'skills': 'Python, Machine Learning, Data Science, Deep Learning',
            'goals': 'Help students learn AI, Share ML expertise',
            'is_mentor': True,
            'bio': 'Senior ML Engineer with 8 years of experience in AI and data science. Passionate about teaching and mentoring.',
            'availability': 'Mon-Wed 6-8 PM, Sat 10 AM-2 PM'
        },
        {
            'name': 'David Rodriguez',
            'email': 'david@skillsync.com',
            'password': 'mentor123',
            'skills': 'JavaScript, React, Node.js, Full-Stack Development',
            'goals': 'Mentor web developers, Build amazing projects',
            'is_mentor': True,
            'bio': 'Full-stack developer and tech lead with expertise in modern web frameworks.',
            'availability': 'Tue-Thu 7-9 PM'
        },
        {
            'name': 'Emily Johnson',
            'email': 'emily@skillsync.com',
            'password': 'mentor123',
            'skills': 'UI/UX Design, Figma, Product Design, User Research',
            'goals': 'Teach design thinking, Improve user experiences',
            'is_mentor': True,
            'bio': 'Product designer with a passion for creating beautiful, user-friendly interfaces.',
            'availability': 'Mon, Wed, Fri 5-7 PM'
        }
    ]
    
    learners_data = [
        {
            'name': 'Alex Kim',
            'email': 'alex@example.com',
            'password': 'learner123',
            'skills': 'HTML, CSS, Basic JavaScript',
            'goals': 'Learn React, Become a web developer, Build portfolio projects',
            'is_mentor': False,
            'bio': 'Aspiring web developer eager to learn modern frameworks.',
            'availability': ''
        },
        {
            'name': 'Maria Garcia',
            'email': 'maria@example.com',
            'password': 'learner123',
            'skills': 'Python basics, Statistics',
            'goals': 'Learn Machine Learning, Data analysis, Career in AI',
            'is_mentor': False,
            'bio': 'Data enthusiast looking to transition into AI and machine learning.',
            'availability': ''
        }
    ]
    
    for mentor_data in mentors_data:
        user = User(**{k: v for k, v in mentor_data.items() if k != 'password'})
        user.set_password(mentor_data['password'])
        db.session.add(user)
    
    for learner_data in learners_data:
        user = User(**{k: v for k, v in learner_data.items() if k != 'password'})
        user.set_password(learner_data['password'])
        db.session.add(user)
    
    db.session.commit()
    
    all_users = User.query.all()
    for user in all_users:
        for skill in user.get_skills_list()[:3]:
            progress = SkillProgress(
                user_id=user.id,
                skill_name=skill,
                level=0.3 if user.is_mentor else 0.2
            )
            db.session.add(progress)
    
    db.session.commit()
    print("Sample data initialized!")

with app.app_context():
    db.create_all()
    init_sample_data()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
