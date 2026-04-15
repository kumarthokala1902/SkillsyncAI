# Flask app main entry
import os
import json
import re
import requests
from collections import Counter
from functools import wraps

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import (db, User, SkillProgress, MentorSession, Post, Poll, Meetup, Career, Startup, Group,
                    PostLike, PostComment, PostSave, PostView, PeerConnection, Notification,
                    AIConversation, AIMessage, LearningPath, MockInterview, CourseProgress,
                    CourseCategory, Course, SkillQuestion, VerificationRequest,
                    CareerApplication, StartupConnection,
                    LiveMeeting, MeetingParticipant, SkillTest, TestResult, MentorFeedback)
from youtube_utils import parse_roadmap_md, get_playlist_videos, get_single_video_as_list
from ai_engine import SkillMatcher
from ai_assistant import SkillSyncAI
from datetime import datetime, timedelta

# ── Firebase (imported lazily – app still works without service account) ──────
from firebase_config import init_firebase, get_client_config
import firebase_service as fs_svc

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skillsync.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

matcher = SkillMatcher()
ai_mentor = SkillSyncAI()

# Initialize Firebase Services
init_firebase()


# ── RBAC Decorators ──────────────────────────────────────────────────────────

def admin_required(f):
    """Restrict a route to users with role == 'admin'."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def mentor_required(f):
    """Restrict a route to mentors and admins."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role not in ('admin', 'mentor'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ── Context Processor – inject Firebase client config into every template ─────

@app.context_processor
def inject_firebase_config():
    return {"firebase_config": get_client_config()}

@app.template_filter('slugify')
def slugify_filter(s):
    if not s:
        return ""
    # Convert to lowercase, replace spaces with hyphens, and remove non-alphanumeric
    s = s.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_-]+', '-', s)
    s = re.sub(r'^-+|-+$', '', s)
    return s


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_notification(user_id, title, message, type='system', link=None):
    """Helper to create a new notification for a user"""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        link=link
    )
    db.session.add(notif)
    db.session.commit()
    return notif

@app.route('/')
def index():
    return render_template('index.html')

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
        role = request.form.get('role', 'student')
        
        # Profile Info based on Role
        skills = request.form.get('skills', '')
        goals = request.form.get('goals', '')
        bio = request.form.get('bio', '')
        
        education_level = request.form.get('education_level')
        college_code = request.form.get('college_code')
        college_name = request.form.get('college_name')
        learning_mode = request.form.get('learning_mode')
        
        expertise = request.form.get('expertise')
        years_experience = request.form.get('years_experience')
        job_role = request.form.get('job_role')
        availability = request.form.get('availability', '')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered locally. Please login.', 'error')
            return redirect(url_for('register'))
        
        # ── Firebase Auth Creation ─────────────────────────────
        import firebase_config
        if firebase_config.fb_auth:
            try:
                # Create user in Firebase Auth
                fb_user = firebase_config.fb_auth.create_user(
                    email=email,
                    password=password,
                    display_name=name
                )
            except Exception as e:
                if 'ALREADY_EXISTS' in str(e).upper() or 'already exists' in str(e).lower():
                    flash('Email already registered in Firebase. Please login.', 'error')
                else:
                    flash(f'Firebase signup failed: {str(e)}', 'error')
                return redirect(url_for('register'))
        else:
            flash('Firebase is not configured. Registration failed.', 'error')
            return redirect(url_for('register'))

        user = User(
            name=name,
            email=email,
            role=role,
            is_mentor=(role == 'mentor'),
            skills=skills,
            goals=goals,
            bio=bio,
            education_level=education_level,
            college_code=college_code,
            college_name=college_name,
            learning_mode=learning_mode,
            expertise=expertise,
            years_experience=int(years_experience) if years_experience and years_experience.isdigit() else 0,
            job_role=job_role,
            availability=availability,
            is_verified=False # Start as unverified per user request
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Add initial skill progress
        for skill in user.get_skills_list():
            progress = SkillProgress(user_id=user.id, skill_name=skill, level=0.2)
            db.session.add(progress)
        db.session.commit()
        
        login_user(user)

        # ── Sync to Firestore (non-blocking) ─────────────────────────────
        fs_svc.sync_user_to_firestore(user)

        flash(f'Welcome to SkillSync, {name}! Your role: {role.capitalize()}. 👋', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Role-based redirect
        if current_user.role in ('mentor',) or current_user.is_mentor:
            return redirect(url_for('mentor_dashboard'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('login.html')

        api_key = os.environ.get('FIREBASE_API_KEY')
        firebase_ok = False

        # ── 1. Try Firebase Auth first ──────────────────────────────────
        if api_key:
            try:
                verify_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
                payload = {"email": email, "password": password, "returnSecureToken": True}
                response = requests.post(verify_url, json=payload, timeout=5)
                response_data = response.json()

                if response.status_code == 200:
                    firebase_ok = True
                else:
                    error_msg = response_data.get('error', {}).get('message', '')
                    if 'INVALID_LOGIN_CREDENTIALS' in error_msg or 'INVALID_PASSWORD' in error_msg or 'EMAIL_NOT_FOUND' in error_msg:
                        # Definitive Firebase rejection — try local fallback below
                        pass
                    else:
                        # Transient Firebase error — fall through to local auth
                        pass
            except Exception as e:
                # Network / timeout — fall through to local auth
                print(f'Firebase login network error: {e}')

        # ── 2. Local password fallback ──────────────────────────────────
        user = User.query.filter_by(email=email).first()

        if firebase_ok:
            if not user:
                flash('User record missing in local database. Please contact support.', 'error')
                return redirect(url_for('login'))
        else:
            # Local auth: verify password against local hash
            if not user or not user.check_password(password):
                flash('Invalid email or password.', 'error')
                return render_template('login.html')

        # ── 3. Login ─────────────────────────────────────────────────────
        if getattr(user, 'is_blocked', False):
            flash('Your account has been suspended. Contact an administrator.', 'error')
            return redirect(url_for('login'))

        login_user(user)
        fs_svc.sync_user_to_firestore(user)
        flash(f'Welcome back, {user.name}! 🔥', 'success')

        # Role-based post-login redirect
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        if user.role in ('mentor',) or user.is_mentor:
            return redirect(url_for('mentor_dashboard'))
        return redirect(url_for('dashboard'))

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

        live_sessions = PeerConnection.query.filter(
            ((PeerConnection.sender_id == current_user.id) | (PeerConnection.receiver_id == current_user.id)) &
            (PeerConnection.status == 'Accepted')
        ).order_by(PeerConnection.created_at.desc()).limit(10).all()
        
        return render_template('dashboard.html', 
                             matches=matches, 
                             match_type=match_type,
                             skill_progress=skill_progress,
                             upcoming_sessions=upcoming_sessions,
                             live_sessions=live_sessions)
    
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
    
    saved_posts = []
    if current_user.id == mentor_id:
        saved_posts = [s.post for s in mentor.saves]
        
    return render_template('mentor.html', mentor=mentor, saved_posts=saved_posts)

@app.route('/learner/<int:learner_id>')
@login_required
def learner_profile(learner_id):
    learner = User.query.get_or_404(learner_id)
    if learner.is_mentor:
        flash('This user is not a learner.', 'error')
        return redirect(url_for('dashboard'))
        
    saved_posts = []
    if current_user.id == learner_id:
        saved_posts = [s.post for s in learner.saves]
        
    return render_template('learner.html', learner=learner, saved_posts=saved_posts)

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
        
        # Fetch peer history
        peer_history = PeerConnection.query.filter(
            (PeerConnection.sender_id == current_user.id) | (PeerConnection.receiver_id == current_user.id),
            PeerConnection.status == 'Completed'
        ).order_by(PeerConnection.created_at.desc()).all()
        
        return render_template('progress.html', skill_progress=skill_progress, peer_history=peer_history)
    
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

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/api/colleges', methods=['GET'])
def get_colleges():
    import csv
    colleges = []
    try:
        with open('anna_university_colleges.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                colleges.append({
                    'code': row.get('College Code', '').strip(),
                    'name': row.get('College Name', '').strip()
                })
    except Exception as e:
        print(f"Error loading CSV: {e}")
    return jsonify(colleges)

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    new_username = data.get('username')
    new_password = data.get('password')
    
    if new_username:
        # Check if username exists? Wait, names don't have to be unique, emails do.
        current_user.name = new_username
    if new_password:
        current_user.set_password(new_password)
        
    college_code = data.get('college_code')
    college_name = data.get('college_name')
    if college_code is not None:
        current_user.college_code = college_code
    if college_name is not None:
        current_user.college_name = college_name
        
    # Also push to firestore if needed, but the periodic sync handles it usually.
    # We will trigger the sync:
    fs_svc.sync_user_to_firestore(current_user)
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated successfully'})

@app.route('/verification')
@login_required
def verification_page():
    lang = request.args.get('lang', 'Python')
    # Check if they already have a pending or approved request to prevent re-testing
    existing = VerificationRequest.query.filter_by(user_id=current_user.id, status='pending').first()
    if existing:
        flash('You already have a pending verification request.', 'info')
        return redirect(url_for('settings'))
        
    if current_user.is_verified:
        flash('You are already verified!', 'success')
        return redirect(url_for('settings'))

    return render_template('verification.html', lang=lang)

@app.route('/api/verification/questions/<category>')
@login_required
def get_verification_questions(category):
    mcqs = SkillQuestion.query.filter_by(category=category, type='mcq').order_by(db.func.random()).limit(5).all()
    coding = SkillQuestion.query.filter_by(category=category, type='coding').order_by(db.func.random()).limit(2).all()
    
    questions = []
    for q in mcqs:
        questions.append({
            'id': q.id,
            'type': 'mcq',
            'text': q.question_text,
            'options': q.get_options(),
            'category': q.category
        })
    for q in coding:
        questions.append({
            'id': q.id,
            'type': 'coding',
            'text': q.question_text,
            'base_code': q.base_code,
            'category': q.category
        })
    
    return jsonify({'success': True, 'questions': questions})

@app.route('/api/verification/submit', methods=['POST'])
@login_required
def submit_verification():
    data = request.json
    language = data.get('language')
    mcq_answers = data.get('mcq_answers') # {q_id: answer}
    coding_answers = data.get('coding_answers') # {q_id: code}
    
    # Calculate MCQ score
    score = 0
    for q_id, ans in mcq_answers.items():
        q = SkillQuestion.query.get(int(q_id))
        if q and q.correct_answer == ans:
            score += 1
            
    req = VerificationRequest(
        user_id=current_user.id,
        role='Mentor' if current_user.is_mentor else 'Student',
        language=language,
        mcq_answers_json=json.dumps(mcq_answers),
        coding_answers_json=json.dumps(coding_answers),
        score=score,
        status='pending'
    )
    
    current_user.verification_status = 'pending'
    db.session.add(req)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Verification submitted! Admin will review soon.'})

@app.route('/api/verify-account', methods=['POST'])
@login_required
def verify_account():
    # Legacy fallback, still keep it but usually the above is used
    current_user.is_verified = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Account verified successfully'})

# Admin Verification Dashboard
@app.route('/admin/verification')
@admin_required
def admin_verification():
    requests = VerificationRequest.query.filter_by(status='pending').order_by(VerificationRequest.submitted_at.desc()).all()
    return render_template('admin_verification.html', verification_requests=requests)

@app.route('/api/admin/verification-action', methods=['POST'])
@admin_required
def admin_verification_action():
    data = request.json
    req_id = data.get('id')
    action = data.get('action') # approve, reject, retest
    notes = data.get('notes', '')
    
    req = VerificationRequest.query.get_or_404(req_id)
    user = User.query.get(req.user_id)
    
    if action == 'approve':
        req.status = 'approved'
        user.is_verified = True
        user.verified_skill = req.language
        user.verified_role = req.role
        user.verification_status = 'approved'
        msg = "Account verified successfully!"
    elif action == 'reject':
        req.status = 'rejected'
        user.verification_status = 'rejected'
        msg = "Verification rejected."
    elif action == 'retest':
        # Delete request to allow user to try again
        db.session.delete(req)
        user.verification_status = 'none'
        user.is_verified = False # In case they were verified before
        db.session.commit()
        return jsonify({'success': True, 'message': 'User can now take the test again.'})
    
    req.reviewer_notes = notes
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = current_user.id
    
    db.session.commit()
    return jsonify({'success': True, 'message': msg})

@app.route('/home')
@login_required
def post_home():
    tag_filter = request.args.get('tag')
    if tag_filter:
        posts = Post.query.filter(Post.content.contains(tag_filter)).order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()

    trending_tags = get_trending_topics(limit=6)

    # --- Sidebar Data ---
    # Upcoming sessions from Firebase
    upcoming_sessions = fs_svc.get_upcoming_sessions()

    # Suggested peers: try Firebase first, fall back to SQLite
    suggested_peers_firebase = fs_svc.get_suggested_peers(exclude_user_id=str(current_user.id), limit=5)
    if suggested_peers_firebase:
        suggested_peers = suggested_peers_firebase
    else:
        # SQLite fallback: pick up to 5 other users
        db_peers = User.query.filter(
            User.id != current_user.id,
            User.role.in_(['student', 'mentor'])
        ).limit(5).all()
        suggested_peers = []
        for p in db_peers:
            skills_list = [s.strip() for s in (p.skills or '').split(',') if s.strip()]
            suggested_peers.append({
                "name": p.name,
                "skill": skills_list[0] if skills_list else "SkillSync Learner",
                "role": p.role,
                "user_id": str(p.id),
                "initial": p.name[0].upper(),
            })

    return render_template('home.html',
        posts=posts,
        trending_tags=trending_tags,
        current_tag=tag_filter,
        upcoming_sessions=upcoming_sessions,
        suggested_peers=suggested_peers,
    )

@app.route('/live-learning')
@login_required
def live_learning():
    sessions = fs_svc.get_live_sessions()
    return render_template('live_learning.html', sessions=sessions)


@app.route('/recordings')
@login_required
def recordings():
    # Fetch categories and courses from database
    categories = CourseCategory.query.order_by(CourseCategory.name).all()
    
    # Get user progress for all courses to show completion percentage
    progress_map = {}
    user_progress = CourseProgress.query.filter_by(user_id=current_user.id).all()
    for p in user_progress:
        progress_map[p.playlist_id] = p.get_completed_videos()

    return render_template('recordings.html', categories=categories, progress_map=progress_map)

@app.route('/course/<playlist_id>')
@login_required
def course_player(playlist_id):
    # Fetch course from database
    course_obj = Course.query.filter_by(playlist_id=playlist_id).first()
    
    if not course_obj:
        flash("Course not found in database", "error")
        return redirect(url_for('recordings'))

    # Get search-friendly dict for template compatibility
    course_info = {
        "title": course_obj.title,
        "instructor": course_obj.instructor,
        "thumbnail": course_obj.thumbnail,
        "playlist_id": course_obj.playlist_id,
        "playlist_link": course_obj.playlist_link
    }

    # Use stored videos or fetch if empty
    videos = course_obj.get_videos()
    if not videos and course_obj.playlist_id:
        # Fallback to fetching once and saving if needed, but for now just fetch
        videos = get_playlist_videos(course_obj.playlist_id)
        if videos:
            course_obj.set_videos(videos)
            db.session.commit()

    # Get user progress
    progress = CourseProgress.query.filter_by(user_id=current_user.id, playlist_id=playlist_id).first()
    completed_videos = progress.get_completed_videos() if progress else []
    last_video_id = progress.last_video_id if progress else None
    
    if not last_video_id and videos:
        last_video_id = videos[0]['id']

    return render_template('course_player.html', 
                           course=course_info, 
                           videos=videos, 
                           completed_videos=completed_videos,
                           last_video_id=last_video_id)

@app.route('/peer-learning')
@login_required
def peer_learning():
    # Discover all students except self
    students = User.query.filter(User.role == 'student', User.id != current_user.id).all()
    return render_template('peer_learning.html', students=students)

@app.route('/api/peer/request', methods=['POST'])
@login_required
def peer_request():
    data = request.json
    receiver_id = data.get('receiver_id')
    topic = data.get('topic')
    scheduled_at_str = data.get('scheduled_at') # e.g. "2024-04-12 18:00"
    
    if not receiver_id or not topic:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    try:
        scheduled_at = datetime.strptime(scheduled_at_str, '%Y-%m-%d %H:%M')
    except:
        scheduled_at = datetime.utcnow()

    # Create Connection
    conn = PeerConnection(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        topic=topic,
        scheduled_at=scheduled_at,
        status='Pending',
        meeting_id=f"peer_{current_user.id}_{receiver_id}_{int(datetime.utcnow().timestamp())}"
    )
    db.session.add(conn)
    
    # Create Notification
    create_notification(
        user_id=receiver_id,
        title="New Peer Learning Request",
        message=f"{current_user.name} sent a peer learning request for '{topic}' on {scheduled_at.strftime('%d %B at %I %p')}",
        type='peer_request',
        link=f"/peer-learning?highlight={conn.id}"
    )
    
    db.session.commit()
    return jsonify({"success": True, "conn_id": conn.id})

@app.route('/api/peer/respond', methods=['POST'])
@login_required
def peer_respond():
    data = request.json
    conn_id = data.get('conn_id')
    response = data.get('response') # accept | reject
    
    conn = PeerConnection.query.get(conn_id)
    if not conn or conn.receiver_id != current_user.id:
        return jsonify({"success": False, "error": "Invalid connection"}), 403

    if response == 'accept':
        conn.status = 'Accepted'
        # Notify sender
        create_notification(
            user_id=conn.sender_id,
            title="Peer Request Accepted!",
            message=f"{current_user.name} accepted your request for '{conn.topic}'. You can now join the live session.",
            type='peer_accepted',
            link=f"/peer-session/{conn.meeting_id}"
        )
    elif response == 'reject':
        conn.status = 'Rejected'
        create_notification(
            user_id=conn.sender_id,
            title="Peer Request Declined",
            message=f"{current_user.name} is unavailable for '{conn.topic}' at this time.",
            type='peer_rejected'
        )
    
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/peer/complete', methods=['POST'])
@login_required
def peer_complete():
    data = request.json
    conn_id = data.get('conn_id')
    rating = data.get('rating')
    feedback = data.get('feedback', '')
    
    conn = PeerConnection.query.get(conn_id)
    if not conn or current_user.id not in (conn.sender_id, conn.receiver_id):
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    conn.status = 'Completed'
    conn.rating = rating
    conn.feedback = feedback
    
    db.session.commit()
    return jsonify({"success": True})

@app.route('/peer-session/<meeting_id>')
@login_required
def peer_session(meeting_id):
    # Verify user is part of this session
    conn = PeerConnection.query.filter_by(meeting_id=meeting_id).first()
    if not conn or current_user.id not in (conn.sender_id, conn.receiver_id):
        abort(403)
        
    other_user = User.query.get(conn.receiver_id if current_user.id == conn.sender_id else conn.sender_id)
    return render_template('peer_room.html', conn=conn, other_user=other_user)

@app.route('/api/course/progress', methods=['POST'])
@login_required
def update_course_progress():
    data = request.json
    playlist_id = data.get('playlist_id')
    video_id = data.get('video_id')
    completed = data.get('completed', False)
    
    if not playlist_id or not video_id:
        return jsonify({"success": False, "error": "Missing data"}), 400
        
    progress = CourseProgress.query.filter_by(user_id=current_user.id, playlist_id=playlist_id).first()
    if not progress:
        progress = CourseProgress(user_id=current_user.id, playlist_id=playlist_id)
        db.session.add(progress)
    
    progress.last_video_id = video_id
    
    if completed:
        completed_list = progress.get_completed_videos()
        if video_id not in completed_list:
            completed_list.append(video_id)
            progress.set_completed_videos(completed_list)
    
    db.session.commit()
    return jsonify({"success": True})

@app.route('/live')
@login_required
def live_sessions():
    return render_template('live.html')

@app.route('/people')
@login_required
def people():
    # Fetch all users except current user
    all_users = User.query.filter(User.id != current_user.id).all()
    
    # Map connection status for each user
    connections = PeerConnection.query.filter(
        (PeerConnection.sender_id == current_user.id) | 
        (PeerConnection.receiver_id == current_user.id)
    ).all()
    
    status_map = {}
    for conn in connections:
        other_id = conn.receiver_id if conn.sender_id == current_user.id else conn.sender_id
        # We prioritize 'Accepted' then 'Pending'
        # If multiple exist (though rare in theory), we take the most relevant one
        if other_id not in status_map or conn.status == 'Accepted':
            # Store both status and who sent it (to handle Acceptance flow)
            status_map[other_id] = {
                'status': conn.status,
                'is_sender': conn.sender_id == current_user.id,
                'conn_id': conn.id
            }
            
    return render_template('people.html', users=all_users, status_map=status_map)

@app.route('/meetups')
@login_required
def meetups():
    now = datetime.now()
    upcoming_meetups = Meetup.query.filter(Meetup.date_time >= now).order_by(Meetup.date_time.asc()).all()
    recent_meetups = Meetup.query.filter(Meetup.date_time < now).order_by(Meetup.date_time.desc()).limit(10).all()
    return render_template('meetups.html', upcoming_meetups=upcoming_meetups, recent_meetups=recent_meetups)

@app.route('/careers')
@login_required
def careers():
    all_careers = Career.query.order_by(Career.created_at.desc()).all()
    return render_template('careers.html', careers=all_careers)

@app.route('/career/<int:career_id>')
@login_required
def career_detail(career_id):
    career = Career.query.get_or_404(career_id)
    return render_template('career_detail.html', career=career)

@app.route('/startups')
@login_required
def startups():
    all_startups = Startup.query.order_by(Startup.created_at.desc()).all()
    return render_template('startups.html', startups=all_startups)

@app.route('/groups')
@login_required
def groups():
    all_groups = Group.query.order_by(Group.created_at.desc()).all()
    return render_template('groups.html', groups=all_groups)

@app.route('/api/groups/add', methods=['POST'])
@login_required
def add_group():
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        location = request.form.get('location')
        mode = request.form.get('mode', 'Online')
        banner_url = request.form.get('banner_url')

        if not name or not description or not category:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('groups'))

        new_group = Group(
            name=name,
            description=description,
            category=category,
            location=location,
            mode=mode,
            banner_url=banner_url,
            creator_id=current_user.id
        )
        db.session.add(new_group)
        db.session.commit()

        # Optional: Sync to Firestore
        # fs_svc.sync_group_to_firestore(...)

        flash('Community Group created successfully! 🚀', 'success')
    except Exception as e:
        flash(f'Error creating group: {str(e)}', 'error')
    
    return redirect(url_for('groups'))

@app.route('/api/meetups/add', methods=['POST'])
@login_required
def add_meetup_user():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        location = request.form.get('location')
        max_participants = request.form.get('max_participants', 50)
        banner_url = request.form.get('banner_url')

        if not title or not description or not date_str or not time_str or not location:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('meetups'))

        # Combine date and time
        date_time = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')

        new_meetup = Meetup(
            title=title,
            description=description,
            date_time=date_time,
            location=location,
            max_participants=int(max_participants),
            banner_url=banner_url,
            organizer_id=current_user.id
        )
        db.session.add(new_meetup)
        db.session.commit()

        # Sync to Firestore
        fs_svc.sync_event_to_firestore(new_meetup)

        flash(f'Meetup "{title}" hosted successfully! 🗓️', 'success')
    except Exception as e:
        flash(f'Error hosting meetup: {str(e)}', 'error')
    
    return redirect(url_for('meetups'))

@app.route('/startup/<int:startup_id>')
@login_required
def startup_detail(startup_id):
    startup = Startup.query.get_or_404(startup_id)
    return render_template('startup_detail.html', startup=startup)

# ── Careers Engagement ────────────────────────────────────────────────────────

@app.route('/career/apply/<int:career_id>', methods=['POST'])
@login_required
def apply_career(career_id):
    career = Career.query.get_or_404(career_id)
    
    # Prevent duplicate applications
    existing = CareerApplication.query.filter_by(career_id=career_id, user_id=current_user.id).first()
    if existing:
        flash('You have already applied for this role.', 'info')
        return redirect(url_for('career_detail', career_id=career_id))
    
    app_record = CareerApplication(
        career_id=career_id,
        user_id=current_user.id,
        status='Pending'
    )
    db.session.add(app_record)
    
    # Notify Poster
    create_notification(
        user_id=career.posted_by_id,
        title='New Job Application',
        message=f'{current_user.name} applied for "{career.title}"',
        type='career',
        link=url_for('career_detail', career_id=career_id)
    )
    
    db.session.commit()
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('career_detail', career_id=career_id))

@app.route('/career/add', methods=['POST'])
@mentor_required
def add_career():
    title = request.form.get('title')
    company = request.form.get('company')
    location = request.form.get('location')
    job_type = request.form.get('job_type', 'Full-time')
    description = request.form.get('description')
    requirements = request.form.get('requirements')
    salary = request.form.get('salary_range')
    
    new_career = Career(
        title=title,
        company=company,
        location=location,
        job_type=job_type,
        description=description,
        requirements=requirements,
        salary_range=salary,
        posted_by_id=current_user.id
    )
    db.session.add(new_career)
    db.session.commit()
    
    flash('Career opportunity posted!', 'success')
    return redirect(url_for('careers'))

@app.route('/career/delete/<int:career_id>', methods=['POST'])
@mentor_required
def delete_career(career_id):
    career = Career.query.get_or_404(career_id)
    if current_user.role != 'admin' and career.posted_by_id != current_user.id:
        abort(403)
        
    db.session.delete(career)
    db.session.commit()
    flash('Post deleted successfully.', 'success')
    return redirect(url_for('careers'))

# ── Startup Engagement ────────────────────────────────────────────────────────

@app.route('/startup/connect/<int:startup_id>', methods=['POST'])
@login_required
def connect_startup(startup_id):
    startup = Startup.query.get_or_404(startup_id)
    
    # Prevent duplicate connections
    existing = StartupConnection.query.filter_by(startup_id=startup_id, user_id=current_user.id).first()
    if existing:
        flash('Connection request already sent.', 'info')
        return redirect(url_for('startup_detail', startup_id=startup_id))
    
    conn = StartupConnection(
        startup_id=startup_id,
        user_id=current_user.id,
        status='Pending',
        message=request.form.get('message', 'I am interested in connecting with your startup.')
    )
    db.session.add(conn)
    
    # Notify Founder
    create_notification(
        user_id=startup.founder_id,
        title='New Startup Connection',
        message=f'{current_user.name} wants to connect with "{startup.name}"',
        type='startup',
        link=url_for('startup_detail', startup_id=startup_id)
    )
    
    db.session.commit()
    flash('Connection request sent to founder!', 'success')
    return redirect(url_for('startup_detail', startup_id=startup_id))

@app.route('/startup/add', methods=['POST'])
@mentor_required
def add_startup():
    name = request.form.get('name')
    industry = request.form.get('industry')
    domain = request.form.get('domain')
    description = request.form.get('description')
    stage = request.form.get('funding_stage')
    website = request.form.get('website')
    
    new_startup = Startup(
        name=name,
        industry=industry,
        domain=domain,
        description=description,
        funding_stage=stage,
        website=website,
        founder_id=current_user.id
    )
    db.session.add(new_startup)
    db.session.commit()
    
    flash('Startup project listed!', 'success')
    return redirect(url_for('startups'))

@app.route('/startup/delete/<int:startup_id>', methods=['POST'])
@mentor_required
def delete_startup(startup_id):
    startup = Startup.query.get_or_404(startup_id)
    if current_user.role != 'admin' and startup.founder_id != current_user.id:
        abort(403)
        
    db.session.delete(startup)
    db.session.commit()
    flash('Startup removed successfully.', 'success')
    return redirect(url_for('startups'))

# ── Admin Management ─────────────────────────────────────────────────────────

@app.route('/admin/careers')
@admin_required
def admin_careers():
    careers_list = Career.query.order_by(Career.created_at.desc()).all()
    return render_template('admin_careers.html', careers=careers_list)

@app.route('/admin/startups')
@admin_required
def admin_startups():
    startups_list = Startup.query.order_by(Startup.created_at.desc()).all()
    return render_template('admin_startups.html', startups=startups_list)

@app.route('/admin/applications')
@admin_required
def admin_applications():
    apps = CareerApplication.query.order_by(CareerApplication.applied_at.desc()).all()
    conns = StartupConnection.query.order_by(StartupConnection.created_at.desc()).all()
    return render_template('admin_interactions.html', applications=apps, connections=conns)

def get_trending_topics(limit=5):
    """
    Calculates top trending hashtags for the current month using a weighted score:
    Score = (Posts * 1.0) + (Likes * 0.5) + (Views * 0.1)
    """
    hashtag_data = {}
    hashtag_regex = re.compile(r'#\w+')
    
    # Filter only this month's posts
    now = datetime.now()
    month_posts = Post.query.filter(
        db.extract('year', Post.created_at) == now.year,
        db.extract('month', Post.created_at) == now.month
    ).all()

    for post in month_posts:
        tags = set(hashtag_regex.findall(post.content or ""))
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in hashtag_data:
                hashtag_data[tag_lower] = {"count": 0, "likes": 0, "views": 0, "posts": []}
            
            hashtag_data[tag_lower]["count"] += 1
            hashtag_data[tag_lower]["likes"] += len(post.likes)
            hashtag_data[tag_lower]["views"] += (post.views_count or 0)
            hashtag_data[tag_lower]["posts"].append(post)

    # Calculate scores
    scored_tags = []
    for tag, stats in hashtag_data.items():
        score = (stats["count"] * 1.0) + (stats["likes"] * 0.5) + (stats["views"] * 0.1)
        scored_tags.append({
            "tag": tag,
            "score": score,
            "count": stats["count"],
            "posts": stats["posts"]
        })

    # Sort by score descending
    scored_tags.sort(key=lambda x: x["score"], reverse=True)
    return scored_tags[:limit]

@app.route('/trending')
@login_required
def trending():
    trending_data = get_trending_topics(limit=10)
    # Reformat for the older template structure if needed, or update template
    top_tags = [(item['tag'], item['count']) for item in trending_data]
    hashtag_to_posts = {item['tag']: item['posts'] for item in trending_data}
    return render_template('trending.html', top_tags=top_tags, hashtag_to_posts=hashtag_to_posts)

@app.route('/api/post/<int:post_id>')
@login_required
def get_post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return jsonify({
        "success": True,
        "post": {
            "id": post.id,
            "content": post.content,
            "link": post.link,
            "created_at": post.created_at.strftime('%b %d, %Y · %I:%M %p'),
            "views_count": post.views_count,
            "likes_count": len(post.likes),
            "comments_count": len(post.comments),
            "author": {
                "name": post.author.name,
                "initial": post.author.name[0],
                "is_mentor": post.author.is_mentor
            },
            "comments": [{
                "content": c.content,
                "author_name": c.author.name,
                "author_initial": c.author.name[0],
                "created_at": c.created_at.strftime('%H:%M')
            } for c in post.comments]
        }
    })

@app.route('/api/post/view/<int:post_id>', methods=['POST'])
@login_required
def track_post_view(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Check if this user has already viewed the post
    existing = PostView.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if not existing:
        view = PostView(post_id=post_id, user_id=current_user.id)
        db.session.add(view)
        db.session.commit()
        return jsonify({"success": True, "views": PostView.query.filter_by(post_id=post_id).count(), "new_view": True})
        
    return jsonify({"success": True, "views": PostView.query.filter_by(post_id=post_id).count(), "new_view": False})

@app.route('/create-post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    link = request.form.get('link')
    poll_question = request.form.get('poll_question')
    poll_options = request.form.get('poll_options')

    if not content:
        flash('Post content cannot be empty.', 'error')
        return redirect(url_for('post_home'))

    post = Post(user_id=current_user.id, content=content, link=link)
    db.session.add(post)
    db.session.flush()

    if poll_question and poll_options:
        options_list = [o.strip() for o in poll_options.split(';') if o.strip()]
        if len(options_list) >= 2:
            poll = Poll(post_id=post.id, question=poll_question, options=';'.join(options_list))
            poll.set_votes_list([0] * len(options_list))
            db.session.add(poll)

    db.session.commit()
    flash('Post created successfully!', 'success')
    return redirect(url_for('post_home'))

@app.route('/vote/<int:poll_id>/<int:option_index>', methods=['POST'])
@login_required
def vote(poll_id, option_index):
    poll = Poll.query.get_or_404(poll_id)
    votes_list = poll.get_votes_list()
    
    if 0 <= option_index < len(votes_list):
        votes_list[option_index] += 1
        poll.set_votes_list(votes_list)
        db.session.commit()
        return jsonify({'success': True, 'votes': votes_list})
    
    return jsonify({'success': False, 'error': 'Invalid option index'}), 400

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

# --- Social Interaction Routes ---

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    existing = PostLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'liked': False})
    
    like = PostLike(post_id=post_id, user_id=current_user.id)
    db.session.add(like)
    db.session.commit()
    
    # Notify post author
    if post.user_id != current_user.id:
        create_notification(
            user_id=post.user_id,
            title="New Like!",
            message=f"{current_user.name} liked your post: \"{post.content[:30]}...\"",
            type="like",
            link=url_for('post_home')
        )
    
    return jsonify({
        'success': True, 
        'liked': True, 
        'likes_count': PostLike.query.filter_by(post_id=post_id).count()
    })

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment_post(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content')
    
    if not content:
        return jsonify({'success': False, 'error': 'Comment cannot be empty'}), 400
    
    comment = PostComment(post_id=post_id, user_id=current_user.id, content=content)
    db.session.add(comment)
    db.session.commit()
    
    # Notify post author
    if post.user_id != current_user.id:
        create_notification(
            user_id=post.user_id,
            title="New Comment!",
            message=f"{current_user.name} commented on your post: \"{content[:30]}...\"",
            type="comment",
            link=url_for('post_home')
        )
    
    return jsonify({
        'success': True,
        'comments_count': PostComment.query.filter_by(post_id=post_id).count(),
        'comment': {
            'author_name': current_user.name,
            'author_initial': current_user.name[0],
            'content': content,
            'created_at': comment.created_at.strftime('%H:%M')
        }
    })

@app.route('/save/<int:post_id>', methods=['POST'])
@login_required
def save_post(post_id):
    post = Post.query.get_or_404(post_id)
    existing = PostSave.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'saved': False})
    
    save = PostSave(post_id=post_id, user_id=current_user.id)
    db.session.add(save)
    db.session.commit()
    return jsonify({'success': True, 'saved': True})

@app.route('/share/<int:post_id>', methods=['POST'])
@login_required
def share_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.share_count += 1
    db.session.commit()
    
    # Generate a shareable link (using hashtag filter as a deep link)
    import re
    tokens = re.findall(r'#\w+', post.content or "")
    tag = tokens[0] if tokens else ""
    share_url = url_for('post_home', tag=tag, _external=True) if tag else url_for('post_home', _external=True)
    
    return jsonify({
        'success': True, 
        'share_count': post.share_count,
        'share_url': share_url,
        'content': post.content
    })

# --- Peer Live Connection Routes ---

@app.route('/api/connect/request/<int:user_id>', methods=['POST'])
@login_required
def request_connection(user_id):
    if current_user.id == user_id:
        return jsonify({'success': False, 'error': 'Cannot connect with yourself'}), 400
        
    target_user = User.query.get_or_404(user_id)
    
    # Check if a pending connection already exists
    existing = PeerConnection.query.filter(
        ((PeerConnection.sender_id == current_user.id) & (PeerConnection.receiver_id == user_id)) |
        ((PeerConnection.sender_id == user_id) & (PeerConnection.receiver_id == current_user.id))
    ).filter(PeerConnection.status == 'Pending').first()
    
    if existing:
        return jsonify({'success': False, 'error': 'A pending connection request already exists'}), 400
        
    new_conn = PeerConnection(sender_id=current_user.id, receiver_id=user_id)
    db.session.add(new_conn)
    db.session.commit()
    
    # Create notification for receiver
    create_notification(
        user_id=user_id,
        title="Live Connection Request",
        message=f"{current_user.name} wants to connect live on Zoom with you.",
        type="connection",
        link=url_for('dashboard')
    )
    
    return jsonify({'success': True, 'connection_id': new_conn.id, 'status': 'Pending'})

def generate_mock_zoom_link():
    import uuid
    meet_id = uuid.uuid4().hex[:8]
    return f"https://zoom.us/j/mock{meet_id}", meet_id

@app.route('/api/connect/accept/<int:connection_id>', methods=['POST'])
@login_required
def accept_connection(connection_id):
    conn = PeerConnection.query.get_or_404(connection_id)
    
    if conn.receiver_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    if conn.status != 'Pending':
        return jsonify({'success': False, 'error': 'Connection is not pending'}), 400
        
    # Mock Zoom API Integration
    zoom_url, zoom_id = generate_mock_zoom_link()
    
    conn.status = 'Accepted'
    conn.zoom_url = zoom_url
    conn.zoom_meeting_id = zoom_id
    conn.expires_at = datetime.utcnow() + timedelta(hours=1)
    
    db.session.commit()
    
    # Create notification for sender
    create_notification(
        user_id=conn.sender_id,
        title="Connection Request Accepted!",
        message=f"{current_user.name} accepted your live connection request. Click to join Zoom.",
        type="connection",
        link=zoom_url
    )
    
    return jsonify({'success': True, 'zoom_url': zoom_url})

@app.route('/api/connect/reject/<int:connection_id>', methods=['POST'])
@login_required
def reject_connection(connection_id):
    conn = PeerConnection.query.get_or_404(connection_id)
    
    if conn.receiver_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    conn.status = 'Rejected'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/connect/notifications', methods=['GET'])
@login_required
def connect_notifications():
    # Find incoming pending requests for the current user
    incoming = PeerConnection.query.filter_by(receiver_id=current_user.id, status='Pending').all()
    
    # Find outgoing requests that have been accepted recently (has a zoom link, hasn't expired)
    now = datetime.utcnow()
    outgoing_accepted = PeerConnection.query.filter(
        PeerConnection.sender_id == current_user.id,
        PeerConnection.status == 'Accepted',
        PeerConnection.expires_at > now
    ).all()
    
    incoming_data = [{
        'id': c.id,
        'sender_id': c.sender_id,
        'sender_name': c.sender.name,
        'created_at': c.created_at.isoformat()
    } for c in incoming]
    
    accepted_data = [{
        'id': c.id,
        'receiver_id': c.receiver_id,
        'receiver_name': c.receiver.name,
        'zoom_url': c.zoom_url
    } for c in outgoing_accepted]
    
    return jsonify({
        'incoming_requests': incoming_data,
        'accepted_requests': accepted_data
    })

@app.route('/notifications')
@login_required
def notifications():
    # Fetch all notifications for the current user
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/api/notifications/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    notif = Notification.query.get_or_404(notification_id)
    if notif.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

# ──────────────────────── AI ASSISTANT ROUTES ────────────────────────

@app.route('/ai-assistant')
@login_required
def ai_assistant_page():
    return render_template('ai_assistant.html')

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')

        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Get or create conversation
        if conversation_id:
            conversation = AIConversation.query.get(conversation_id)
            if not conversation or conversation.user_id != current_user.id:
                conversation = None

        if not conversation_id or not conversation:
            conversation = AIConversation(user_id=current_user.id, title=message[:50])
            db.session.add(conversation)
            db.session.flush()

        # Save user message
        user_msg = AIMessage(conversation_id=conversation.id, role='user', content=message)
        db.session.add(user_msg)

        # Build history from conversation
        history = [{'role': m.role, 'content': m.content} for m in conversation.messages]

        # Get AI response
        result = ai_mentor.chat(current_user, message, history)
        response_text = result.get('response', 'I\'m here to help!')
        action = result.get('action')
        confidence = result.get('confidence', 80)

        # Handle action-triggered responses
        action_data = None
        if action == 'profile_analysis':
            action_data = ai_mentor.analyze_profile(current_user)
            response_text += "\n\n" + _format_profile_analysis(action_data)
        elif action == 'learning_path':
            action_data = ai_mentor.generate_learning_path(current_user)
            response_text += "\n\n" + _format_learning_path(action_data)
        elif action == 'weekly_insights':
            action_data = ai_mentor.weekly_insights(current_user, db.session)
            response_text += "\n\n" + _format_weekly_insights(action_data)
        elif action == 'connection_suggestions':
            all_users = User.query.all()
            action_data = ai_mentor.suggest_connections(current_user, all_users)
            response_text += "\n\n" + _format_connections(action_data)

        # Save assistant message
        ai_msg = AIMessage(conversation_id=conversation.id, role='assistant',
                           content=response_text, context_type=action or result.get('intent'),
                           confidence=confidence)
        if action_data:
            ai_msg.set_metadata(action_data if not isinstance(action_data, list) else {'suggestions': action_data})

        db.session.add(ai_msg)
        db.session.commit()

        return jsonify({
            'response': response_text,
            'conversation_id': conversation.id,
            'confidence': confidence,
            'action': action,
            'action_data': action_data,
        })
    except Exception as e:
        print(f"AI Chat error: {e}")
        return jsonify({'response': 'Apologies, something went wrong. Please try again!', 'confidence': 0}), 500


def _format_profile_analysis(data):
    lines = [f"**Profile Strength: {data['score']}/100 ({data['grade']} — {data['grade_label']})**\n"]
    lines.append(data['summary'] + "\n")
    if data['tips']:
        lines.append("**Improvement Tips:**")
        for tip in data['tips'][:5]:
            lines.append(f"• {tip}")
    if data['skill_gap']['missing_skills']:
        lines.append(f"\n**Skill Gaps for {data['skill_gap']['target_role'].title()}:**")
        for s in data['skill_gap']['missing_skills'][:5]:
            lines.append(f"• {s['skill']} ({s['priority']} priority)")
    return "\n".join(lines)


def _format_learning_path(data):
    lines = [data['summary'] + "\n"]
    for m in data['milestones'][:6]:
        icon = "✅" if m['status'] == 'completed' else "🔵" if m['status'] == 'in_progress' else "🔒"
        lines.append(f"{icon} **{m['order']}. {m['skill']}** — {m['domain']} (≈{m['estimated_days']} days)")
        if m['resources']:
            lines.append(f"   Resources: {', '.join(m['resources'][:2])}")
    lines.append(f"\n📊 Progress: {data['completion_percentage']}% | ⏱️ ~{data['estimated_weeks_remaining']} weeks remaining")
    return "\n".join(lines)


def _format_weekly_insights(data):
    lines = [f"**{data['summary']}**\n"]
    lines.append(data['trend_message'] + "\n")
    for h in data['highlights']:
        lines.append(f"{h}")
    m = data['metrics']
    lines.append(f"\n📊 Posts: {m['posts']} | Sessions: {m['sessions_completed']} | Skills Updated: {m['skills_updated']} | Connections: {m['connections']}")
    return "\n".join(lines)


def _format_connections(suggestions):
    if not suggestions:
        return "No suggestions available right now. Try adding more skills and goals to your profile!"
    lines = ["**Recommended Connections:**\n"]
    for s in suggestions[:5]:
        lines.append(f"🤝 **{s['name']}** ({s['role']}) — {s['match_score']}% match")
        lines.append(f"   {s['reason']}")
        lines.append(f"   Skills: {', '.join(s['skills'][:4])}")
    return "\n".join(lines)


@app.route('/api/ai/profile-analysis', methods=['POST'])
@login_required
def ai_profile_analysis():
    try:
        result = ai_mentor.analyze_profile(current_user)
        return jsonify(result)
    except Exception as e:
        print(f"Profile analysis error: {e}")
        return jsonify({'error': 'Failed to analyze profile'}), 500


@app.route('/api/ai/job-match/<int:career_id>')
@login_required
def ai_job_match(career_id):
    try:
        career = Career.query.get_or_404(career_id)
        result = ai_mentor.job_match(current_user, career)
        return jsonify(result)
    except Exception as e:
        print(f"Job match error: {e}")
        return jsonify({'error': 'Failed to compute job match'}), 500


@app.route('/api/ai/learning-path', methods=['POST'])
@login_required
def ai_learning_path():
    try:
        result = ai_mentor.generate_learning_path(current_user)

        # Persist to DB
        goals_str = ', '.join(current_user.get_goals_list()[:3])
        lp = LearningPath(
            user_id=current_user.id,
            goal=goals_str or 'Career Growth',
            completion_pct=result['completion_percentage']
        )
        lp.set_milestones(result['milestones'])
        db.session.add(lp)
        db.session.commit()

        return jsonify(result)
    except Exception as e:
        print(f"Learning path error: {e}")
        return jsonify({'error': 'Failed to generate learning path'}), 500


@app.route('/api/ai/mock-interview', methods=['POST'])
@login_required
def ai_mock_interview():
    try:
        data = request.get_json()
        action = data.get('action', 'start')  # start, answer, finish
        interview_type = data.get('type', 'technical')

        if action == 'start':
            # Start new interview
            interview_data = ai_mentor.start_interview(current_user, interview_type)

            interview = MockInterview(
                user_id=current_user.id,
                interview_type=interview_type,
                questions_json=json.dumps(interview_data['questions']),
                current_question=0
            )
            # Store keywords/topics in internal metadata
            interview.scores_json = json.dumps([])
            interview.answers_json = json.dumps([])
            interview.feedback_json = json.dumps([])
            db.session.add(interview)
            db.session.commit()

            # Store keyword data in session for evaluation
            session[f'interview_{interview.id}_keywords'] = interview_data['keywords']
            session[f'interview_{interview.id}_topics'] = interview_data['topics']

            return jsonify({
                'interview_id': interview.id,
                'interview_type': interview_type,
                'total_questions': len(interview_data['questions']),
                'current_question': 0,
                'question': interview_data['questions'][0] if interview_data['questions'] else None,
            })

        elif action == 'answer':
            interview_id = data.get('interview_id')
            answer = data.get('answer', '')

            interview = MockInterview.query.get_or_404(interview_id)
            if interview.user_id != current_user.id:
                return jsonify({'error': 'Unauthorized'}), 403

            questions = interview.get_questions()
            answers = interview.get_answers()
            scores = interview.get_scores()
            feedback_list = interview.get_feedback()
            q_idx = interview.current_question

            # Get keywords from session
            keywords = session.get(f'interview_{interview.id}_keywords', [[]] * len(questions))
            topics = session.get(f'interview_{interview.id}_topics', ['General'] * len(questions))

            # Build interview_data dict for evaluation
            eval_data = {'keywords': keywords, 'topics': topics}
            result = ai_mentor.evaluate_answer(answer, q_idx, eval_data)

            # Store
            answers.append(answer)
            scores.append(result['score'])
            feedback_list.append(result['feedback'])
            interview.answers_json = json.dumps(answers)
            interview.scores_json = json.dumps(scores)
            interview.feedback_json = json.dumps(feedback_list)
            interview.current_question = q_idx + 1

            # Check if done
            is_last = (q_idx + 1) >= len(questions)
            next_question = None if is_last else questions[q_idx + 1]

            if is_last:
                interview.is_complete = True
                interview.overall_score = round(sum(scores) / len(scores)) if scores else 0
                final_result = ai_mentor.finish_interview({
                    'scores': scores, 'topics': topics, 'feedback': feedback_list
                })
                result['final_result'] = final_result

            db.session.commit()

            return jsonify({
                'interview_id': interview.id,
                'current_question': q_idx + 1,
                'total_questions': len(questions),
                'evaluation': result,
                'next_question': next_question,
                'is_complete': is_last,
            })

        elif action == 'finish':
            interview_id = data.get('interview_id')
            interview = MockInterview.query.get_or_404(interview_id)
            if interview.user_id != current_user.id:
                return jsonify({'error': 'Unauthorized'}), 403

            topics = session.get(f'interview_{interview.id}_topics', [])
            final = ai_mentor.finish_interview({
                'scores': interview.get_scores(),
                'topics': topics,
                'feedback': interview.get_feedback()
            })
            return jsonify(final)

        return jsonify({'error': 'Invalid action'}), 400
    except Exception as e:
        print(f"Mock interview error: {e}")
        return jsonify({'error': 'Failed to process mock interview'}), 500


@app.route('/api/ai/weekly-insights')
@login_required
def ai_weekly_insights():
    try:
        result = ai_mentor.weekly_insights(current_user, db.session)
        return jsonify(result)
    except Exception as e:
        print(f"Weekly insights error: {e}")
        return jsonify({'error': 'Failed to generate insights'}), 500


@app.route('/api/ai/connection-suggestions')
@login_required
def ai_connection_suggestions():
    try:
        all_users = User.query.all()
        result = ai_mentor.suggest_connections(current_user, all_users)
        return jsonify({'suggestions': result})
    except Exception as e:
        print(f"Connection suggestions error: {e}")
        return jsonify({'error': 'Failed to generate suggestions'}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # --- Handle Default Admin Bypass ---
        if (email == 'admin@skillsync.com' or email == 'admin') and password == 'admin123':
            user = User.query.filter_by(email='admin@skillsync.com').first()
            if not user:
                # Create default admin in SQLite
                user = User(
                    name='Super Admin',
                    email='admin@skillsync.com',
                    role='admin',
                    is_verified=True
                )
                user.set_password('admin123')
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            flash('Welcome back, System Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        api_key = os.environ.get('FIREBASE_API_KEY')
        verify_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        
        try:
            response = requests.post(verify_url, json=payload)
            if response.status_code == 200:
                user = User.query.filter_by(email=email).first()
                if not user or user.role != 'admin':
                    flash('Unauthorized access. Admin credentials required.', 'error')
                    return redirect(url_for('admin_login'))
                
                login_user(user)
                flash(f'Welcome back, Admin {user.name}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials.', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
            
    return render_template('admin_login.html')

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Super Admin dashboard – user table + analytics."""
    try:
        all_users = User.query.order_by(User.created_at.desc()).all()
        all_careers = Career.query.order_by(Career.created_at.desc()).all()
        all_startups = Startup.query.order_by(Startup.created_at.desc()).all()
        all_meetups = Meetup.query.order_by(Meetup.date_time.desc()).all()
        
        total_users   = len(all_users)
        total_admins  = sum(1 for u in all_users if u.role == 'admin')
        total_mentors = sum(1 for u in all_users if u.role == 'mentor')
        total_students = sum(1 for u in all_users if u.role == 'student')
        total_blocked  = sum(1 for u in all_users if getattr(u, 'is_blocked', False))

        # Firestore analytics (returns zeros gracefully if Firebase is off)
        fs_analytics = fs_svc.get_firestore_analytics()

        # Engagement Metrics
        total_applications = CareerApplication.query.count()
        total_connections = StartupConnection.query.count()

        return render_template(
            'admin_dashboard.html',
            all_users=all_users,
            all_careers=all_careers,
            all_startups=all_startups,
            all_meetups=all_meetups,
            total_users=total_users,
            total_admins=total_admins,
            total_mentors=total_mentors,
            total_students=total_students,
            total_blocked=total_blocked,
            total_applications=total_applications,
            total_connections=total_connections,
            fs_analytics=fs_analytics,
        )
    except Exception as exc:
        flash(f'Error loading admin dashboard: {exc}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', all_users=all_users)

@app.route('/admin/posts')
@login_required
@admin_required
def admin_posts():
    all_posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin_posts.html', all_posts=all_posts)

@app.route('/admin/peer-learning')
@login_required
@admin_required
def admin_peer():
    # Show active and completed sessions
    all_sessions = PeerConnection.query.order_by(PeerConnection.created_at.desc()).all()
    return render_template('admin_peer.html', all_sessions=all_sessions)

@app.route('/admin/recordings')
@login_required
@admin_required
def admin_recordings():
    categories = CourseCategory.query.all()
    courses = Course.query.all()
    return render_template('admin_recordings.html', categories=categories, courses=courses)

@app.route('/admin/trending')
@login_required
@admin_required
def admin_trending():
    from app import get_trending_topics # Ensure helper is accessible
    trending_data = get_trending_topics(limit=20)
    return render_template('admin_trending.html', trending_data=trending_data)

@app.route('/admin/user/block/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_block_user(user_id):
    """Toggle block/unblock for a user."""
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot block yourself'}), 400
    user = User.query.get_or_404(user_id)
    user.is_blocked = not getattr(user, 'is_blocked', False)
    db.session.commit()
    # Mirror to Firestore
    fs_svc.block_user_in_firestore(user_id, user.is_blocked)
    action = 'blocked' if user.is_blocked else 'unblocked'
    return jsonify({'success': True, 'blocked': user.is_blocked, 'message': f'User {action} successfully'})


@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Permanently delete a user (admin only)."""
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_dashboard'))
    user = User.query.get_or_404(user_id)
    user_name = user.name
    db.session.delete(user)
    db.session.commit()
    # Mirror to Firestore
    fs_svc.delete_user_from_firestore(user_id)
    flash(f'User "{user_name}" has been permanently deleted.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/user/approve-mentor/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_approve_mentor(user_id):
    """Promote a student to mentor role."""
    user = User.query.get_or_404(user_id)
    user.role = 'mentor'
    user.is_mentor = True
    db.session.commit()
    fs_svc.update_user_role_in_firestore(user_id, 'mentor')
    return jsonify({'success': True, 'message': f'{user.name} has been approved as a Mentor'})


@app.route('/admin/user/demote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_demote_user(user_id):
    """Demote a mentor back to student."""
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot demote yourself'}), 400
    user = User.query.get_or_404(user_id)
    user.role = 'student'
    user.is_mentor = False
    db.session.commit()
    fs_svc.update_user_role_in_firestore(user_id, 'student')
    return jsonify({'success': True, 'message': f'{user.name} has been demoted to Student'})


@app.route('/admin/category/create', methods=['POST'])
@login_required
@admin_required
def admin_create_category():
    name = request.form.get('name')
    if name:
        new_cat = CourseCategory(name=name)
        db.session.add(new_cat)
        db.session.commit()
        flash(f'Category "{name}" created successfully.', 'success')
    return redirect(url_for('admin_recordings'))

@app.route('/admin/course/create', methods=['POST'])
@login_required
@admin_required
def admin_create_course():
    course_id = request.form.get('course_id')
    title = request.form.get('title')
    instructor = request.form.get('instructor')
    playlist_link = request.form.get('playlist_link')
    category_id = request.form.get('category_id')
    thumbnail = request.form.get('thumbnail')
    
    # Extract playlist ID from URL
    plist_id = None
    if 'list=' in playlist_link:
        plist_id = re.search(r'list=([a-zA-Z0-9_-]+)', playlist_link).group(1)
    
    if course_id: # Edit
        course = Course.query.get(course_id)
        course.title = title
        course.instructor = instructor
        course.playlist_link = playlist_link
        course.playlist_id = plist_id or course.playlist_id
        course.category_id = category_id
        if thumbnail: course.thumbnail = thumbnail
        flash(f'Course "{title}" updated.', 'success')
    else: # Create
        new_course = Course(
            title=title,
            instructor=instructor,
            playlist_link=playlist_link,
            playlist_id=plist_id,
            category_id=category_id,
            thumbnail=thumbnail or 'https://i.ytimg.com/vi/placeholder/0.jpg'
        )
        # Fetch initial videos
        if plist_id:
            videos = get_playlist_videos(plist_id)
            new_course.set_videos(videos)
        
        db.session.add(new_course)
        flash(f'Course "{title}" added to library.', 'success')
    
    db.session.commit()
    return redirect(url_for('admin_recordings'))

@app.route('/admin/course/delete/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_course(item_id):
    course = Course.query.get_or_404(item_id)
    db.session.delete(course)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Course deleted.'})

@app.route('/api/course/<int:course_id>')
def api_get_course(course_id):
    course = Course.query.get_or_404(course_id)
    return jsonify({
        'id': course.id,
        'title': course.title,
        'instructor': course.instructor,
        'playlist_link': course.playlist_link,
        'category_id': course.category_id,
        'thumbnail': course.thumbnail
    })

@app.route('/admin/post/delete/<int:post_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Post removed successfully.'})

@app.route('/admin/cleanup-duplicates', methods=['POST'])
@login_required
@admin_required
def admin_cleanup_duplicates():
    """Trigger Firestore duplicate cleanup across all collections."""
    result = fs_svc.cleanup_all_duplicates()
    return jsonify({'success': True, 'result': result})


@app.route('/admin/bootstrap', methods=['GET', 'POST'])
@login_required
def admin_bootstrap():
    """
    One-time route to promote the currently logged-in user to Super Admin.
    Requires ADMIN_BOOTSTRAP_TOKEN from .env.
    Disabled once at least one admin exists in the DB.
    """
    # Disable if an admin already exists
    if User.query.filter_by(role='admin').count() > 0:
        flash('Admin already exists. Bootstrap is disabled.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        token = request.form.get('token', '')
        expected = os.environ.get('ADMIN_BOOTSTRAP_TOKEN', '')
        if not expected:
            flash('ADMIN_BOOTSTRAP_TOKEN not configured in .env', 'error')
            return redirect(url_for('dashboard'))
        if token != expected:
            flash('Invalid bootstrap token.', 'error')
            return render_template('admin_bootstrap.html')

        current_user.role = 'admin'
        current_user.is_mentor = False
        db.session.commit()
        fs_svc.update_user_role_in_firestore(current_user.id, 'admin')
        flash(f'🎉 {current_user.name} is now Super Admin!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_bootstrap.html')


@app.route('/admin/peer/cancel/<int:session_id>', methods=['POST'])
@login_required
@admin_required
def admin_cancel_peer(session_id):
    session_obj = PeerConnection.query.get_or_404(session_id)
    session_obj.status = 'Cancelled'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Session cancelled by administrator.'})

@app.route('/api/admin/analytics')
@login_required
@admin_required
def admin_analytics_api():
    """JSON endpoint: returns SQLite + Firestore counts for the admin dashboard."""
    try:
        sql_counts = {
            'users':    User.query.count(),
            'mentors':  User.query.filter_by(role='mentor').count(),
            'students': User.query.filter_by(role='student').count(),
            'blocked':  User.query.filter_by(is_blocked=True).count(),
            'posts':    Post.query.count(),
            'sessions': PeerConnection.query.filter_by(status='Accepted').count(), # Active Sessions
            'meetups':  Meetup.query.count(),
            'courses':  Course.query.count()
        }
        fs_counts = fs_svc.get_firestore_analytics()
        return jsonify({'sql': sql_counts, 'firestore': fs_counts})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ── Data Management (Careers, Startups, Events) ───────────────────────────────

@app.route('/admin/career/create', methods=['POST'])
@login_required
@admin_required
def admin_create_career():
    try:
        c = Career(
            title=request.form.get('title'),
            company=request.form.get('company'),
            location=request.form.get('location'),
            description=request.form.get('description'),
            requirements=request.form.get('requirements'),
            salary_range=request.form.get('salary_range'),
            posted_by_id=current_user.id
        )
        db.session.add(c)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Career created successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/career/delete/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_career(item_id):
    c = Career.query.get_or_404(item_id)
    title = c.title
    db.session.delete(c)
    db.session.commit()
    flash(f'Career "{title}" deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/startup/create', methods=['POST'])
@login_required
@admin_required
def admin_create_startup():
    try:
        s = Startup(
            name=request.form.get('name'),
            industry=request.form.get('industry'),
            description=request.form.get('description'),
            funding_stage=request.form.get('funding_stage'),
            website=request.form.get('website'),
            founder_id=current_user.id
        )
        db.session.add(s)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Startup created successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/startup/delete/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_startup(item_id):
    s = Startup.query.get_or_404(item_id)
    name = s.name
    db.session.delete(s)
    db.session.commit()
    flash(f'Startup "{name}" deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/meetup/create', methods=['POST'])
@login_required
@admin_required
def admin_create_meetup():
    try:
        date_str = request.form.get('date_time')
        date_obj = datetime.fromisoformat(date_str) if date_str else datetime.now()
        
        m = Meetup(
            title=request.form.get('title'),
            description=request.form.get('description'),
            location=request.form.get('location'),
            date_time=date_obj,
            organizer_id=current_user.id
        )
        db.session.add(m)
        db.session.commit()
        
        # Mirror event to real-time Firestore layer
        if hasattr(fs_svc, 'sync_event_to_firestore'):
            fs_svc.sync_event_to_firestore(m)
            
        return jsonify({'success': True, 'message': 'Event hosted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/meetup/delete/<int:item_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_meetup(item_id):
    m = Meetup.query.get_or_404(item_id)
    title = m.title
    db.session.delete(m)
    db.session.commit()
    
    if hasattr(fs_svc, 'delete_event_from_firestore'):
        fs_svc.delete_event_from_firestore(item_id)
        
    flash(f'Event "{title}" deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

# ───────────────────────────────────────────────────────────────────────────── #

# ══════════════════════════════════════════════════════════════════════════════
#  MENTOR DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/mentor/dashboard')
@login_required
@mentor_required
def mentor_dashboard():
    """Dedicated mentor control panel."""
    try:
        # Live meetings created by this mentor
        meetings = LiveMeeting.query.filter_by(creator_id=current_user.id).order_by(
            LiveMeeting.scheduled_at.desc()
        ).all()

        # Auto-update statuses
        for m in meetings:
            m.auto_update_status()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Students who booked sessions with this mentor
        booked_sessions = MentorSession.query.filter_by(mentor_id=current_user.id).all()
        students_ids = list({s.learner_id for s in booked_sessions})
        students = User.query.filter(User.id.in_(students_ids)).all() if students_ids else []

        # Aggregated stats
        total_meetings = len(meetings)
        live_meetings = [m for m in meetings if m.status == 'live']
        upcoming_meetings = [m for m in meetings if m.status == 'upcoming']
        completed_meetings = [m for m in meetings if m.status == 'completed']

        feedback_list = MentorFeedback.query.filter_by(mentor_id=current_user.id).all()
        avg_rating = (
            round(sum(f.rating for f in feedback_list) / len(feedback_list), 1)
            if feedback_list else 0
        )

        completed_sessions = MentorSession.query.filter_by(
            mentor_id=current_user.id, status='completed'
        ).count()

        # Skill tests this mentor created
        skill_tests = SkillTest.query.filter_by(creator_id=current_user.id).order_by(
            SkillTest.created_at.desc()
        ).all()

        return render_template(
            'mentor_dashboard.html',
            meetings=meetings,
            live_meetings=live_meetings,
            upcoming_meetings=upcoming_meetings,
            completed_meetings=completed_meetings,
            students=students,
            total_meetings=total_meetings,
            avg_rating=avg_rating,
            completed_sessions=completed_sessions,
            feedback_list=feedback_list,
            skill_tests=skill_tests,
        )
    except Exception as e:
        flash(f'Error loading mentor dashboard: {e}', 'error')
        print(f'mentor_dashboard error: {e}')
        return redirect(url_for('dashboard'))


# ── Mentor Stats API ─────────────────────────────────────────────────────────

@app.route('/api/mentor/<int:mentor_id>/stats')
@login_required
def mentor_stats(mentor_id):
    """Dynamic stats for a mentor's public profile."""
    try:
        mentor = User.query.get_or_404(mentor_id)
        if not mentor.is_mentor:
            return jsonify({'error': 'Not a mentor'}), 400

        sessions_completed = MentorSession.query.filter_by(
            mentor_id=mentor_id, status='completed'
        ).count()

        students_set = {s.learner_id for s in MentorSession.query.filter_by(mentor_id=mentor_id).all()}
        students_mentored = len(students_set)

        feedback = MentorFeedback.query.filter_by(mentor_id=mentor_id).all()
        avg_rating = round(sum(f.rating for f in feedback) / len(feedback), 1) if feedback else 0

        total_meetings = LiveMeeting.query.filter_by(creator_id=mentor_id).count()

        return jsonify({
            'success': True,
            'students_mentored': students_mentored,
            'sessions_completed': sessions_completed,
            'avg_rating': avg_rating,
            'total_meetings': total_meetings,
            'years_experience': mentor.years_experience or 0,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  LIVE MEETING CRUD
# ══════════════════════════════════════════════════════════════════════════════

def _auto_generate_meeting_link():
    """Generate a unique Google Meet-style link."""
    import uuid
    code = uuid.uuid4().hex[:10]
    return f"https://meet.google.com/{code[:3]}-{code[3:7]}-{code[7:]}"


@app.route('/api/meetings', methods=['GET'])
@login_required
def get_meetings():
    """List all live meetings with optional filters."""
    try:
        skill = request.args.get('skill', '').strip()
        language = request.args.get('language', '').strip()
        status_filter = request.args.get('status', '').strip()
        mentor_only = request.args.get('mentor_only', 'false').lower() == 'true'

        query = LiveMeeting.query

        if mentor_only and (current_user.role in ('mentor', 'admin')):
            query = query.filter_by(creator_id=current_user.id)

        if skill:
            query = query.filter(LiveMeeting.skill_category.ilike(f'%{skill}%'))
        if language:
            query = query.filter(LiveMeeting.language.ilike(f'%{language}%'))
        if status_filter:
            query = query.filter_by(status=status_filter)

        meetings = query.order_by(LiveMeeting.scheduled_at.asc()).all()

        # Auto-update statuses
        changed = False
        for m in meetings:
            old_status = m.status
            m.auto_update_status()
            if m.status != old_status:
                changed = True
        if changed:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

        return jsonify({
            'success': True,
            'meetings': [m.to_dict() for m in meetings],
            'total': len(meetings)
        })
    except Exception as e:
        print(f'get_meetings error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meetings/create', methods=['POST'])
@login_required
@mentor_required
def create_meeting():
    """Create a new live meeting (mentor only)."""
    try:
        data = request.get_json() or {}

        title = data.get('title', '').strip()
        if not title:
            return jsonify({'success': False, 'error': 'Title is required'}), 400

        scheduled_str = data.get('scheduled_at', '')
        try:
            scheduled_at = datetime.fromisoformat(scheduled_str)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid date/time format'}), 400

        meeting_link = data.get('meeting_link', '').strip()
        if not meeting_link or data.get('auto_generate_link'):
            meeting_link = _auto_generate_meeting_link()

        meeting = LiveMeeting(
            title=title,
            description=data.get('description', ''),
            language=data.get('language', 'English'),
            skill_category=data.get('skill_category', 'General'),
            scheduled_at=scheduled_at,
            duration_minutes=int(data.get('duration_minutes', 60)),
            meeting_link=meeting_link,
            max_participants=int(data.get('max_participants', 50)),
            status=data.get('status', 'upcoming'),
            creator_id=current_user.id,
        )
        db.session.add(meeting)
        db.session.commit()

        # Sync to Firestore for real-time updates
        fs_svc.sync_meeting_to_firestore(meeting)

        return jsonify({'success': True, 'meeting': meeting.to_dict()})
    except Exception as e:
        db.session.rollback()
        print(f'create_meeting error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meetings/<int:meeting_id>', methods=['GET'])
@login_required
def get_meeting(meeting_id):
    """Get a single meeting's details."""
    try:
        meeting = LiveMeeting.query.get_or_404(meeting_id)
        meeting.auto_update_status()
        return jsonify({'success': True, 'meeting': meeting.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meetings/<int:meeting_id>/update', methods=['POST'])
@login_required
@mentor_required
def update_meeting(meeting_id):
    """Update a live meeting — only upcoming meetings, only by creator."""
    try:
        meeting = LiveMeeting.query.get_or_404(meeting_id)

        # Ownership check
        if meeting.creator_id != current_user.id and current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Only allow editing upcoming meetings
        if meeting.status not in ('upcoming', 'live') and current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Cannot edit a completed or cancelled meeting'}), 400

        data = request.get_json() or {}

        if 'title' in data:
            meeting.title = data['title'].strip()
        if 'description' in data:
            meeting.description = data['description']
        if 'language' in data:
            meeting.language = data['language']
        if 'skill_category' in data:
            meeting.skill_category = data['skill_category']
        if 'scheduled_at' in data:
            meeting.scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        if 'duration_minutes' in data:
            meeting.duration_minutes = int(data['duration_minutes'])
        if 'meeting_link' in data:
            link = data['meeting_link'].strip()
            meeting.meeting_link = link if link else _auto_generate_meeting_link()
        if 'max_participants' in data:
            meeting.max_participants = int(data['max_participants'])
        if 'status' in data:
            meeting.status = data['status']

        meeting.updated_at = datetime.utcnow()
        db.session.commit()
        fs_svc.sync_meeting_to_firestore(meeting)

        return jsonify({'success': True, 'meeting': meeting.to_dict()})
    except Exception as e:
        db.session.rollback()
        print(f'update_meeting error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meetings/<int:meeting_id>/delete', methods=['POST'])
@login_required
@mentor_required
def delete_meeting(meeting_id):
    """Delete a meeting — only by creator (or admin)."""
    try:
        meeting = LiveMeeting.query.get_or_404(meeting_id)

        if meeting.creator_id != current_user.id and current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        db.session.delete(meeting)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Meeting deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print(f'delete_meeting error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meetings/<int:meeting_id>/join', methods=['POST'])
@login_required
def join_meeting(meeting_id):
    """Student joins a live meeting."""
    try:
        meeting = LiveMeeting.query.get_or_404(meeting_id)
        meeting.auto_update_status()

        if meeting.status == 'completed':
            return jsonify({'success': False, 'error': 'This meeting has ended'}), 400
        if meeting.is_full:
            return jsonify({'success': False, 'error': 'Meeting is full'}), 400

        # Check if already joined
        existing = MeetingParticipant.query.filter_by(
            meeting_id=meeting_id, user_id=current_user.id
        ).first()

        if not existing:
            participant = MeetingParticipant(meeting_id=meeting_id, user_id=current_user.id)
            db.session.add(participant)

            # Notify mentor
            create_notification(
                user_id=meeting.creator_id,
                title='New Meeting Participant',
                message=f'{current_user.name} joined your meeting "{meeting.title}"',
                type='meeting',
                link=url_for('mentor_dashboard')
            )
            db.session.commit()

        return jsonify({
            'success': True,
            'meeting_link': meeting.meeting_link,
            'participant_count': meeting.participant_count
        })
    except Exception as e:
        db.session.rollback()
        print(f'join_meeting error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meetings/<int:meeting_id>/participants', methods=['GET'])
@login_required
@mentor_required
def meeting_participants(meeting_id):
    """View participants for a meeting (mentor only)."""
    try:
        meeting = LiveMeeting.query.get_or_404(meeting_id)

        if meeting.creator_id != current_user.id and current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        participants = [{
            'user_id': p.user_id,
            'name': p.user.name,
            'email': p.user.email,
            'role': p.user.role,
            'joined_at': p.joined_at.strftime('%I:%M %p') if p.joined_at else 'N/A',
        } for p in meeting.participants]

        return jsonify({'success': True, 'participants': participants, 'count': len(participants)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/meetings/live-status', methods=['GET'])
@login_required
def meetings_live_status():
    """Lightweight polling endpoint for real-time meeting status + participant counts."""
    try:
        meetings = LiveMeeting.query.filter(
            LiveMeeting.status.in_(['upcoming', 'live'])
        ).all()

        for m in meetings:
            m.auto_update_status()

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

        return jsonify({
            'meetings': [
                {
                    'id': m.id,
                    'status': m.status,
                    'participant_count': m.participant_count,
                    'is_full': m.is_full,
                }
                for m in meetings
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  SKILL TESTS (Mentor)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/skill-tests', methods=['GET'])
@login_required
def get_skill_tests():
    """List active skill tests (students see all; mentors see their own)."""
    try:
        if current_user.role in ('mentor', 'admin'):
            tests = SkillTest.query.filter_by(creator_id=current_user.id).order_by(SkillTest.created_at.desc()).all()
        else:
            tests = SkillTest.query.filter_by(is_active=True).order_by(SkillTest.created_at.desc()).all()

        return jsonify({'success': True, 'tests': [{
            'id': t.id,
            'title': t.title,
            'skill_category': t.skill_category,
            'description': t.description,
            'pass_score': t.pass_score,
            'time_limit_minutes': t.time_limit_minutes,
            'question_count': len(t.get_questions()),
            'is_active': t.is_active,
            'creator_name': t.creator.name,
            'created_at': t.created_at.strftime('%b %d, %Y'),
        } for t in tests]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skill-tests/create', methods=['POST'])
@login_required
@mentor_required
def create_skill_test():
    """Create a new skill test."""
    try:
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        skill_category = data.get('skill_category', '').strip()

        if not title or not skill_category:
            return jsonify({'success': False, 'error': 'Title and skill_category are required'}), 400

        test = SkillTest(
            title=title,
            skill_category=skill_category,
            description=data.get('description', ''),
            pass_score=int(data.get('pass_score', 60)),
            time_limit_minutes=int(data.get('time_limit_minutes', 30)),
            creator_id=current_user.id,
        )
        test.set_questions(data.get('questions', []))
        db.session.add(test)
        db.session.commit()

        return jsonify({'success': True, 'test_id': test.id, 'message': 'Skill test created!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skill-tests/<int:test_id>/delete', methods=['POST'])
@login_required
@mentor_required
def delete_skill_test(test_id):
    """Delete a skill test (creator or admin only)."""
    try:
        test = SkillTest.query.get_or_404(test_id)
        if test.creator_id != current_user.id and current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        db.session.delete(test)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Test deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  MENTOR FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/feedback/submit', methods=['POST'])
@login_required
def submit_mentor_feedback():
    """Student submits feedback/rating for a mentor after a session."""
    try:
        data = request.get_json() or {}
        mentor_id = data.get('mentor_id')
        rating = int(data.get('rating', 5))
        comment = data.get('comment', '')
        session_id = data.get('session_id')

        if not mentor_id:
            return jsonify({'success': False, 'error': 'mentor_id is required'}), 400
        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400

        mentor = User.query.get_or_404(mentor_id)
        if not mentor.is_mentor:
            return jsonify({'success': False, 'error': 'User is not a mentor'}), 400

        if current_user.id == mentor_id:
            return jsonify({'success': False, 'error': 'Cannot rate yourself'}), 400

        # Upsert
        fb = MentorFeedback.query.filter_by(
            mentor_id=mentor_id, student_id=current_user.id, session_id=session_id
        ).first()
        if fb:
            fb.rating = rating
            fb.comment = comment
        else:
            fb = MentorFeedback(
                mentor_id=mentor_id,
                student_id=current_user.id,
                rating=rating,
                comment=comment,
                session_id=session_id,
            )
            db.session.add(fb)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Feedback submitted! Thank you.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/feedback/mentor/<int:mentor_id>', methods=['GET'])
@login_required
def get_mentor_feedback(mentor_id):
    """Get all public feedback for a mentor."""
    try:
        feedback = MentorFeedback.query.filter_by(mentor_id=mentor_id).order_by(
            MentorFeedback.created_at.desc()
        ).all()
        data = [{
            'rating': f.rating,
            'comment': f.comment,
            'student_name': f.student.name,
            'student_initial': f.student.name[0].upper(),
            'created_at': f.created_at.strftime('%b %d, %Y'),
        } for f in feedback]
        avg = round(sum(f.rating for f in feedback) / len(feedback), 1) if feedback else 0
        return jsonify({'success': True, 'feedback': data, 'avg_rating': avg, 'total': len(data)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def init_sample_data():
    pass


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
    app.run(host='0.0.0.0', port=5004, debug=True)