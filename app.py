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

@app.route('/peer-learning')
def peer_learning():
    return render_template('peer_learning.html')

@app.route('/provide-meet-link', methods=['GET', 'POST'])
@login_required
def provide_meet_link():
    if request.method == 'POST':
        meet_link = request.form.get('meet_link')
        mentor_name = request.form.get('mentor_name')

        flash(f"Google Meet link shared successfully by {mentor_name}!", "success")
        return redirect(url_for('peer_learning'))

    return render_template('provide_meet_link.html')

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
    try:
        # Get all users based on current user role
        if current_user.is_mentor:
            # Show all learners to mentors
            matches = User.query.filter_by(is_mentor=False).all()
            match_type = 'learners'
        else:
            # Show all mentors to learners
            matches = User.query.filter_by(is_mentor=True).all()
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
    
    except Exception as e:
        flash('Error loading dashboard. Please try again.', 'error')
        print(f"Dashboard error: {e}")
        # Return empty data to prevent template errors
        return render_template('dashboard.html', 
                             matches=[], 
                             match_type='mentors',
                             skill_progress=[],
                             upcoming_sessions=[])

@app.route('/mentor/<int:mentor_id>')
@login_required
def mentor_profile(mentor_id):
    mentor = User.query.get_or_404(mentor_id)
    if not mentor.is_mentor:
        flash('This user is not a mentor.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('mentor.html', mentor=mentor)

@app.route('/learner/<int:learner_id>')
@login_required
def learner_profile(learner_id):
    learner = User.query.get_or_404(learner_id)
    if learner.is_mentor:
        flash('This user is not a learner.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('learner.html', learner=learner)

@app.route('/book-session/<int:mentor_id>', methods=['POST'])
@login_required
def book_session(mentor_id):
    try:
        mentor = User.query.get_or_404(mentor_id)
        
        if not mentor.is_mentor:
            flash('This user is not a mentor.', 'error')
            return redirect(url_for('dashboard'))
        
        scheduled_time_str = request.form.get('scheduled_time')
        topic = request.form.get('topic', '')
        duration = int(request.form.get('duration', 30))
        
        if not scheduled_time_str or not topic:
            flash('Please provide all required fields.', 'error')
            return redirect(url_for('mentor_profile', mentor_id=mentor_id))
        
        scheduled_time = datetime.fromisoformat(scheduled_time_str)
        
        # Check if session is in the future
        if scheduled_time <= datetime.now():
            flash('Please select a future date and time.', 'error')
            return redirect(url_for('mentor_profile', mentor_id=mentor_id))
        
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
    
    except Exception as e:
        flash('Error booking session. Please try again.', 'error')
        print(f"Book session error: {e}")
        return redirect(url_for('mentor_profile', mentor_id=mentor_id))

@app.route('/sessions')
@login_required
def sessions():
    try:
        # Get sessions where current user is either mentor or learner
        all_sessions = MentorSession.query.filter(
            (MentorSession.learner_id == current_user.id) | 
            (MentorSession.mentor_id == current_user.id)
        ).order_by(MentorSession.scheduled_time).all()
        
        # Separate sessions by role
        mentor_sessions = [s for s in all_sessions if s.mentor_id == current_user.id]
        learner_sessions = [s for s in all_sessions if s.learner_id == current_user.id]
        
        return render_template('sessions.html',
                             mentor_sessions=mentor_sessions,
                             learner_sessions=learner_sessions)
    
    except Exception as e:
        flash('Error loading sessions. Please try again.', 'error')
        print(f"Sessions error: {e}")
        return render_template('sessions.html',
                             mentor_sessions=[],
                             learner_sessions=[])

@app.route('/update-session-status/<int:session_id>', methods=['POST'])
@login_required
def update_session_status(session_id):
    try:
        session = MentorSession.query.get_or_404(session_id)
        
        # Check if current user is either mentor or learner in this session
        if session.mentor_id != current_user.id and session.learner_id != current_user.id:
            flash('You are not authorized to modify this session.', 'error')
            return redirect(url_for('sessions'))
        
        new_status = request.form.get('status')
        meet_link = request.form.get('meet_link', '')
        
        if new_status in ['scheduled', 'completed', 'cancelled']:
            session.status = new_status
            if meet_link:
                session.meet_link = meet_link
            
            db.session.commit()
            flash(f'Session status updated to {new_status}!', 'success')
        else:
            flash('Invalid status.', 'error')
        
        return redirect(url_for('sessions'))
    
    except Exception as e:
        flash('Error updating session. Please try again.', 'error')
        print(f"Update session error: {e}")
        return redirect(url_for('sessions'))

@app.route('/progress')
@login_required
def progress():
    try:
        skill_progress = SkillProgress.query.filter_by(user_id=current_user.id).order_by(SkillProgress.skill_name).all()
        return render_template('progress.html', skill_progress=skill_progress)
    
    except Exception as e:
        flash('Error loading progress. Please try again.', 'error')
        print(f"Progress error: {e}")
        return render_template('progress.html', skill_progress=[])

@app.route('/api/progress-data')
@login_required
def progress_data():
    try:
        skill_progress = SkillProgress.query.filter_by(user_id=current_user.id).order_by(SkillProgress.skill_name).all()
        
        data = {
            'labels': [sp.skill_name for sp in skill_progress],
            'values': [sp.level * 100 for sp in skill_progress]
        }
        return jsonify(data)
    
    except Exception as e:
        print(f"Progress data API error: {e}")
        return jsonify({'labels': [], 'values': []})

@app.route('/update-progress/<int:skill_id>', methods=['POST'])
@login_required
def update_progress(skill_id):
    try:
        skill = SkillProgress.query.get_or_404(skill_id)
        
        if skill.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        skill.update_progress(0.1)
        db.session.commit()
        
        return jsonify({'success': True, 'new_level': skill.level * 100})
    
    except Exception as e:
        print(f"Update progress error: {e}")
        return jsonify({'error': 'Failed to update progress'}), 500

def init_sample_data():
    """Initialize sample data for testing"""
    print("Initializing sample data...")
    
    # Check if we already have data
    if User.query.count() > 0:
        print("Sample data already exists.")
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
            'availability': 'Weekends 2-5 PM'
        },
        {
            'name': 'Maria Garcia',
            'email': 'maria@example.com',
            'password': 'learner123',
            'skills': 'Python basics, Statistics',
            'goals': 'Learn Machine Learning, Data analysis, Career in AI',
            'is_mentor': False,
            'bio': 'Data enthusiast looking to transition into AI and machine learning.',
            'availability': 'Evenings after 7 PM'
        },
        {
            'name': 'John Smith',
            'email': 'john@example.com',
            'password': 'learner123',
            'skills': 'Java, Spring Boot, Database Design',
            'goals': 'Learn Microservices, Cloud Computing, System Design',
            'is_mentor': False,
            'bio': 'Backend developer looking to expand into distributed systems.',
            'availability': 'Weekdays 6-9 PM'
        },
        {
            'name': 'Lisa Wang',
            'email': 'lisa@example.com',
            'password': 'learner123',
            'skills': 'Digital Marketing, SEO, Content Strategy',
            'goals': 'Learn Data Analytics, Growth Marketing, Product Management',
            'is_mentor': False,
            'bio': 'Marketing professional transitioning into tech product roles.',
            'availability': 'Flexible hours'
        }
    ]
    
    # Create mentor users
    for mentor_data in mentors_data:
        user = User(
            name=mentor_data['name'],
            email=mentor_data['email'],
            skills=mentor_data['skills'],
            goals=mentor_data['goals'],
            is_mentor=mentor_data['is_mentor'],
            bio=mentor_data['bio'],
            availability=mentor_data['availability']
        )
        user.set_password(mentor_data['password'])
        db.session.add(user)
    
    # Create learner users
    for learner_data in learners_data:
        user = User(
            name=learner_data['name'],
            email=learner_data['email'],
            skills=learner_data['skills'],
            goals=learner_data['goals'],
            is_mentor=learner_data['is_mentor'],
            bio=learner_data['bio'],
            availability=learner_data['availability']
        )
        user.set_password(learner_data['password'])
        db.session.add(user)
    
    db.session.commit()
    print("Users created successfully.")
    
    # Create skill progress for all users
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
    print("Skill progress created successfully.")
    
    # Create sample sessions
    mentors = User.query.filter_by(is_mentor=True).all()
    learners = User.query.filter_by(is_mentor=False).all()
    
    if mentors and learners:
        sample_sessions = [
            {
                'mentor': mentors[0],
                'learner': learners[0],
                'topic': 'Introduction to Machine Learning',
                'scheduled_time': datetime.now() + timedelta(days=1, hours=2),
                'duration': 60,
                'meet_link': 'https://meet.google.com/abc-defg-hij'
            },
            {
                'mentor': mentors[1],
                'learner': learners[1],
                'topic': 'React Fundamentals',
                'scheduled_time': datetime.now() + timedelta(days=2, hours=3),
                'duration': 45,
                'meet_link': 'https://meet.google.com/klm-nopq-rst'
            },
            {
                'mentor': mentors[2],
                'learner': learners[2],
                'topic': 'UI/UX Design Principles',
                'scheduled_time': datetime.now() + timedelta(days=3, hours=1),
                'duration': 90,
                'meet_link': 'https://meet.google.com/uvw-xyz-123'
            }
        ]
        
        for session_data in sample_sessions:
            session = MentorSession(
                mentor_id=session_data['mentor'].id,
                learner_id=session_data['learner'].id,
                topic=session_data['topic'],
                scheduled_time=session_data['scheduled_time'],
                duration_minutes=session_data['duration'],
                status='scheduled',
                meet_link=session_data['meet_link']
            )
            db.session.add(session)
    
    db.session.commit()
    print("Sample sessions created successfully.")
    print("Sample data initialization complete!")

# Initialize database
with app.app_context():
    try:
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully.")
        
        # Initialize sample data
        init_sample_data()
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        # If there's an error, drop all tables and try again
        try:
            db.drop_all()
            db.create_all()
            init_sample_data()
        except Exception as e2:
            print(f"Failed to reinitialize database: {e2}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)