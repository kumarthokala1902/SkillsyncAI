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
    skills = db.Column(db.Text, nullable=False, default='')
    goals = db.Column(db.Text, nullable=False, default='')
    bio = db.Column(db.Text, default='')
    is_mentor = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='student')  # admin | mentor | student
    is_blocked = db.Column(db.Boolean, default=False)
    education_level = db.Column(db.String(100))
    college_code = db.Column(db.String(50))
    college_name = db.Column(db.String(255))
    learning_mode = db.Column(db.String(50))
    expertise = db.Column(db.String(200))
    years_experience = db.Column(db.Integer)
    job_role = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    verified_skill = db.Column(db.String(100))
    verified_role = db.Column(db.String(20))
    verification_status = db.Column(db.String(20), default='none') # none | pending | approved | rejected
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
    
    # Careers posted by the user
    careers = db.relationship('Career', backref='poster', lazy=True, cascade='all, delete-orphan')
    
    # Startups founded by the user
    startups = db.relationship('Startup', backref='founder', lazy=True, cascade='all, delete-orphan')

    # Course Progress tracking
    course_progress = db.relationship('CourseProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        # Use pbkdf2:sha256 explicitly — avoids scrypt incompatibility with macOS LibreSSL
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_skills_list(self):
        return [s.strip() for s in self.skills.split(',') if s.strip()]
    
    def get_goals_list(self):
        return [g.strip() for g in self.goals.split(',') if g.strip()]
    
    @property
    def connection_count(self):
        """Returns the number of accepted/completed peer connections."""
        sent = [c for c in self.sent_connections if c.status in ('Accepted', 'Completed')]
        received = [c for c in self.received_connections if c.status in ('Accepted', 'Completed')]
        return len(sent) + len(received)

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

class MentorBooking(db.Model):
    """Student-initiated booking request for a 1-on-1 mentor session."""
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(300), nullable=False)  # Acts as 'skill'
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, default=60)           # minutes
    mode = db.Column(db.String(20), default='video')       # video | audio | chat
    status = db.Column(db.String(20), default='pending')   # pending | accepted | rejected | cancelled
    meeting_link = db.Column(db.String(500))
    message = db.Column(db.Text, default='')
    reject_reason = db.Column(db.String(300), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mentor  = db.relationship('User', foreign_keys=[mentor_id],  backref=db.backref('received_bookings', lazy=True))
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('sent_bookings',     lazy=True))
    meeting = db.relationship('MentorBookingMeeting', 
                              primaryjoin="MentorBooking.id == MentorBookingMeeting.booking_id",
                              foreign_keys="MentorBookingMeeting.booking_id",
                              backref=db.backref('booking_link', uselist=False),
                              uselist=False)

    @property
    def start_datetime(self):
        return datetime.combine(self.date, self.time)

    @property
    def end_datetime(self):
        return self.start_datetime + __import__('datetime').timedelta(minutes=self.duration)

    def to_dict(self):
        return {
            'id': self.id,
            'mentor_id': self.mentor_id,
            'student_id': self.student_id,
            'mentor_name': self.mentor.name if self.mentor else '',
            'student_name': self.student.name if self.student else '',
            'topic': self.topic,
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'date_display': self.date.strftime('%b %d, %Y') if self.date else '',
            'time': self.time.strftime('%H:%M') if self.time else '',
            'time_display': self.time.strftime('%I:%M %p') if self.time else '',
            'duration': self.duration,
            'mode': self.mode,
            'status': self.status,
            'meeting_id': self.meeting.id if self.meeting else None,
            'meeting_link': self.meeting_link or '',
            'message': self.message or '',
            'reject_reason': self.reject_reason or '',
            'created_at': self.created_at.isoformat() if self.created_at else '',
            'is_active': self.status == 'accepted' and datetime.utcnow() >= self.start_datetime and datetime.utcnow() <= self.end_datetime
        }

    def __repr__(self):
        return f'<MentorBooking {self.id} {self.status}>'

class MentorBookingMeeting(db.Model):
    """Automated WebRTC meeting associated with a mentor booking."""
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('mentor_booking.id'), nullable=True) # Linked after creation
    room_id = db.Column(db.String(100), unique=True, nullable=False)
    meeting_link = db.Column(db.String(500))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    # status: upcoming | live | completed | cancelled
    status = db.Column(db.String(20), default='upcoming')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_joinable(self):
        now = datetime.utcnow()
        return self.status == 'upcoming' and now >= (self.start_time - __import__('datetime').timedelta(minutes=5)) and now <= self.end_time

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'meeting_link': self.meeting_link,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'status': self.status,
            'is_joinable': self.is_joinable()
        }

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    share_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    
    author = db.relationship('User', backref=db.backref('posts', lazy=True, cascade='all, delete-orphan'))
    poll = db.relationship('Poll', backref='post', uselist=False, cascade='all, delete-orphan')
    likes = db.relationship('PostLike', backref='post', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('PostComment', backref='post', lazy=True, cascade='all, delete-orphan')
    saves = db.relationship('PostSave', backref='post', lazy=True, cascade='all, delete-orphan')
    views = db.relationship('PostView', backref='post', lazy=True, cascade='all, delete-orphan')

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    question = db.Column(db.String(200), nullable=False)
    options = db.Column(db.Text, nullable=False)  # Semicolon-separated options
    votes = db.Column(db.Text, default='') # Semicolon-separated vote counts (e.g., "0;0;0")

    def get_options_list(self):
        return [o.strip() for o in self.options.split(';') if o.strip()]

    def get_votes_list(self):
        if not self.votes:
            return [0] * len(self.get_options_list())
        return [int(v) for v in self.votes.split(';') if v.strip()]

    def set_votes_list(self, votes_list):
        self.votes = ';'.join(map(str, votes_list))

class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can only like a post once
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='_post_user_like_uc'),)

    user = db.relationship('User', backref=db.backref('likes', lazy=True))

class PostSave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can only save a post once
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='_post_user_save_uc'),)

    user = db.relationship('User', backref=db.backref('saves', lazy=True))

class PostView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='_post_user_view_uc'),)

    user = db.relationship('User', backref=db.backref('views', lazy=True))

    def __repr__(self):
        return f'<PostView {self.user_id} on {self.post_id}>'

class PostComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref=db.backref('comments', lazy=True))

class Meetup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    max_participants = db.Column(db.Integer, default=50)
    banner_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organizer = db.relationship('User', backref=db.backref('meetups', lazy=True))

    def __repr__(self):
        return f'<Meetup {self.title}>'

class Career(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    job_type = db.Column(db.String(50), default='Full-time')  # Internship, Full-time, Remote
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    salary_range = db.Column(db.String(100))
    posted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    applications = db.relationship('CareerApplication', backref='career', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Career {self.title} at {self.company}>'

class Startup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(100)) # e.g. Healthcare, Fintech, Edtech
    description = db.Column(db.Text, nullable=False)
    funding_stage = db.Column(db.String(100))
    website = db.Column(db.String(500))
    founder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    connections = db.relationship('StartupConnection', backref='startup', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Startup {self.name}>'

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    mode = db.Column(db.String(50), default='Online') # Online / Offline
    banner_url = db.Column(db.String(500))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref=db.backref('groups', lazy=True))

    def __repr__(self):
        return f'<Group {self.name}>'

class CareerApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    career_id = db.Column(db.Integer, db.ForeignKey('career.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Reviewed, Accepted, Rejected
    resume_url = db.Column(db.String(500))
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('career_applications', lazy=True))

    def __repr__(self):
        return f'<CareerApplication {self.user_id} for {self.career_id}>'

class StartupConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey('startup.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Accepted, Rejected
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('startup_connections', lazy=True))

    def __repr__(self):
        return f'<StartupConnection {self.user_id} with {self.startup_id}>'

class PeerConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Accepted, Rejected, Completed
    topic = db.Column(db.String(200))
    scheduled_at = db.Column(db.DateTime)
    meeting_id = db.Column(db.String(100), unique=True) # Firestore doc ID
    rating = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    zoom_url = db.Column(db.String(500))
    zoom_meeting_id = db.Column(db.String(100))

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_connections', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_connections', lazy=True))

    def __repr__(self):
        return f'<PeerConnection {self.id} ({self.status})>'

class PeerRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skills_expected = db.Column(db.String(500))  # JSON or comma-separated
    skills_offered = db.Column(db.String(500))
    peer_mode = db.Column(db.Boolean, default=False)
    date = db.Column(db.Date)
    time = db.Column(db.Time)
    duration = db.Column(db.Integer, default=30)  # Session duration in minutes
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending') # Pending, Accepted, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_peer_reqs', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_peer_reqs', lazy=True))

class PeerSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Caller / Learner in 1-way
    user_b_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Receiver / Teacher
    session_type = db.Column(db.String(50), default='one-way') # one-way, peer-mode-1, peer-mode-2
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='scheduled') # scheduled, live, completed, cancelled
    video_link = db.Column(db.String(500))
    associated_request_id = db.Column(db.Integer, db.ForeignKey('peer_request.id'), nullable=True)

    user_a = db.relationship('User', foreign_keys=[user_a_id])
    user_b = db.relationship('User', foreign_keys=[user_b_id])
    request = db.relationship('PeerRequest', backref=db.backref('sessions', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(20)) # 'connection', 'like', 'comment', 'system'
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'

class AIConversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), default='New Chat')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('ai_conversations', lazy=True))
    messages = db.relationship('AIMessage', backref='conversation', lazy=True, cascade='all, delete-orphan', order_by='AIMessage.created_at')

    def __repr__(self):
        return f'<AIConversation {self.id} for User {self.user_id}>'

class AIMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('ai_conversation.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    context_type = db.Column(db.String(50))  # 'profile_analysis', 'job_match', 'learning_path', etc
    confidence = db.Column(db.Integer, default=0)
    metadata_json = db.Column(db.Text, default='{}')  # Extra structured data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_metadata(self):
        import json
        try:
            return json.loads(self.metadata_json or '{}')
        except:
            return {}

    def set_metadata(self, data):
        import json
        self.metadata_json = json.dumps(data)

    def __repr__(self):
        return f'<AIMessage {self.role}: {self.content[:40]}>'

class LearningPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal = db.Column(db.String(300), nullable=False)
    milestones_json = db.Column(db.Text, default='[]')
    current_milestone = db.Column(db.Integer, default=0)
    completion_pct = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('learning_paths', lazy=True))

    def get_milestones(self):
        import json
        try:
            return json.loads(self.milestones_json or '[]')
        except:
            return []

    def set_milestones(self, milestones):
        import json
        self.milestones_json = json.dumps(milestones)

    def __repr__(self):
        return f'<LearningPath {self.goal} ({self.completion_pct}%)>'

class MockInterview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interview_type = db.Column(db.String(50), default='technical')
    questions_json = db.Column(db.Text, default='[]')
    answers_json = db.Column(db.Text, default='[]')
    scores_json = db.Column(db.Text, default='[]')
    feedback_json = db.Column(db.Text, default='[]')
    overall_score = db.Column(db.Integer, default=0)
    current_question = db.Column(db.Integer, default=0)
    is_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('mock_interviews', lazy=True))

    def get_questions(self):
        import json
        try:
            return json.loads(self.questions_json or '[]')
        except:
            return []

    def get_answers(self):
        import json
        try:
            return json.loads(self.answers_json or '[]')
        except:
            return []

    def get_scores(self):
        import json
        try:
            return json.loads(self.scores_json or '[]')
        except:
            return []

    def get_feedback(self):
        import json
        try:
            return json.loads(self.feedback_json or '[]')
        except:
            return []

    def __repr__(self):
        return f'<MockInterview {self.interview_type} score={self.overall_score}>'

class CourseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    playlist_id = db.Column(db.String(100), nullable=False)
    # Store completed video IDs as a JSON-encoded list
    completed_videos_json = db.Column(db.Text, default='[]')
    last_video_id = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_completed_videos(self):
        import json
        try:
            return json.loads(self.completed_videos_json or '[]')
        except:
            return []

    def set_completed_videos(self, video_ids):
        import json
        self.completed_videos_json = json.dumps(video_ids)

    def __repr__(self):
        return f'<CourseProgress user={self.user_id} playlist={self.playlist_id}>'

class CourseCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    courses = db.relationship('Course', backref='category', lazy=True)

    def __repr__(self):
        return f'<CourseCategory {self.name}>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    instructor = db.Column(db.String(100))
    thumbnail = db.Column(db.String(500))
    playlist_id = db.Column(db.String(100), unique=True) # Usually the part after list=
    playlist_link = db.Column(db.String(500), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('course_category.id'))
    # Storing videos summary as JSON for quick access
    videos_json = db.Column(db.Text, default='[]') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_videos(self):
        import json
        try:
            return json.loads(self.videos_json or '[]')
        except:
            return []

    def set_videos(self, videos):
        import json
        self.videos_json = json.dumps(videos)

    def __repr__(self):
        return f'<Course {self.title}>'

class SkillQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # python, java, javascript, cpp, devops, dsa
    type = db.Column(db.String(20), nullable=False) # mcq, coding
    question_text = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, default='[]') # For MCQs: JSON list of strings
    correct_answer = db.Column(db.String(200)) # For MCQs: the correct option index or text
    base_code = db.Column(db.Text) # For coding: starter code
    difficulty = db.Column(db.String(20), default='medium')

    def get_options(self):
        import json
        try:
            return json.loads(self.options_json or '[]')
        except:
            return []

class VerificationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    mcq_answers_json = db.Column(db.Text, default='{}') # JSON mapping question_id to selection
    coding_answers_json = db.Column(db.Text, default='{}') # JSON mapping question_id to code
    score = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewer_notes = db.Column(db.Text)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('verification_requests', lazy=True))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref=db.backref('reviewed_requests', lazy=True))


# ─── Live Meeting Management ───────────────────────────────────────────────────

class LiveMeeting(db.Model):
    """A public live meeting created by a mentor for students to join."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    language = db.Column(db.String(50), default='English')           # Meeting language
    skill_category = db.Column(db.String(100), default='General')    # e.g. Python, DSA, ML
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    meeting_link = db.Column(db.String(500), default='')             # External meet URL or auto-generated
    max_participants = db.Column(db.Integer, default=50)
    # Status: upcoming | live | completed | cancelled
    status = db.Column(db.String(20), default='upcoming')
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship('User', backref=db.backref('live_meetings', lazy=True, cascade='all, delete-orphan'))
    participants = db.relationship('MeetingParticipant', backref='meeting', lazy=True, cascade='all, delete-orphan')

    @property
    def participant_count(self):
        return len(self.participants)

    @property
    def is_full(self):
        return self.participant_count >= self.max_participants

    def auto_update_status(self):
        """Auto-flip status based on current time."""
        now = datetime.utcnow()
        end_time = self.scheduled_at + __import__('datetime').timedelta(minutes=self.duration_minutes)
        if now >= end_time:
            self.status = 'completed'
        elif now >= self.scheduled_at:
            self.status = 'live'
        else:
            self.status = 'upcoming'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'language': self.language,
            'skill_category': self.skill_category,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'scheduled_at_display': self.scheduled_at.strftime('%b %d, %Y · %I:%M %p') if self.scheduled_at else '',
            'duration_minutes': self.duration_minutes,
            'meeting_link': self.meeting_link,
            'max_participants': self.max_participants,
            'participant_count': self.participant_count,
            'status': self.status,
            'creator_id': self.creator_id,
            'creator_name': self.creator.name if self.creator else '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<LiveMeeting {self.title} ({self.status})>'


class MeetingParticipant(db.Model):
    """Tracks which user joined which live meeting."""
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('live_meeting.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('meeting_id', 'user_id', name='_meeting_user_uc'),)

    user = db.relationship('User', backref=db.backref('meeting_participations', lazy=True))

    def __repr__(self):
        return f'<MeetingParticipant user={self.user_id} meeting={self.meeting_id}>'


# ─── Skill Tests ───────────────────────────────────────────────────────────────

class SkillTest(db.Model):
    """A test created by a mentor to assess student skills."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    skill_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    questions_json = db.Column(db.Text, default='[]')   # JSON list of {question, options, answer}
    pass_score = db.Column(db.Integer, default=60)       # Minimum % to pass
    time_limit_minutes = db.Column(db.Integer, default=30)
    is_active = db.Column(db.Boolean, default=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref=db.backref('skill_tests', lazy=True))
    results = db.relationship('TestResult', backref='test', lazy=True, cascade='all, delete-orphan')

    def get_questions(self):
        import json
        try:
            return json.loads(self.questions_json or '[]')
        except:
            return []

    def set_questions(self, questions):
        import json
        self.questions_json = json.dumps(questions)

    def __repr__(self):
        return f'<SkillTest {self.title}>'


class TestResult(db.Model):
    """Records a student's result on a SkillTest."""
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('skill_test.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)        # Percentage 0-100
    passed = db.Column(db.Boolean, default=False)
    answers_json = db.Column(db.Text, default='{}')
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('test_results', lazy=True))

    def __repr__(self):
        return f'<TestResult user={self.user_id} test={self.test_id} score={self.score}>'


# ─── Feedback / Ratings ────────────────────────────────────────────────────────

class MentorFeedback(db.Model):
    """Student feedback and rating for a mentor."""
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, default=5)       # 1-5 stars
    comment = db.Column(db.Text, default='')
    session_id = db.Column(db.Integer, db.ForeignKey('mentor_session.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('mentor_id', 'student_id', 'session_id', name='_mentor_student_session_uc'),)

    mentor = db.relationship('User', foreign_keys=[mentor_id], backref=db.backref('received_feedback', lazy=True))
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('given_feedback', lazy=True))

    def __repr__(self):
        return f'<MentorFeedback mentor={self.mentor_id} student={self.student_id} rating={self.rating}>'
