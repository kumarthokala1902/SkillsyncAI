# SkillSync - AI-Powered Mentorship Platform

## Overview
SkillSync is a Flask-based mentorship platform that intelligently connects learners with mentors using AI-powered matching. The platform analyzes users' skills and goals to suggest the best mentor-learner pairs, enabling personalized learning journeys.

**Tagline:** "Where AI Connects Minds to Learn, Grow & Shine Together"

## Project Status
✅ MVP Complete - Fully functional with all core features implemented

## Architecture

### Backend (Flask + Python)
- **Framework:** Flask 3.0.0
- **Database:** SQLite (SQLAlchemy ORM)
- **Authentication:** Flask-Login with password hashing
- **AI Matching:** scikit-learn TF-IDF for skill-based recommendations

### Frontend
- **Styling:** TailwindCSS (via CDN for development)
- **Charts:** Chart.js for skill progress visualization
- **Design:** Modern UI with soft gradients, rounded cards, and animations

### Project Structure
```
SkillSync/
├── app.py                      # Main Flask application with all routes
├── models.py                   # Database models (User, SkillProgress, MentorSession)
├── ai_engine/
│   ├── recommender.py          # AI matching algorithm using TF-IDF
│   └── __init__.py
├── templates/
│   ├── base.html               # Base template with navigation
│   ├── index.html              # Landing page
│   ├── register.html           # User registration
│   ├── login.html              # Login page
│   ├── dashboard.html          # Personalized dashboard with AI matches
│   ├── mentor.html             # Mentor profile and session booking
│   └── progress.html           # Skill progress tracking with charts
├── static/                     # Static assets (empty for now)
├── requirements.txt            # Python dependencies
└── .gitignore
```

## Core Features

### 1. User Authentication
- Registration with skills, goals, and mentor/learner role selection
- Secure login with password hashing (Werkzeug)
- Session management via Flask-Login

### 2. AI-Powered Matching
- TF-IDF vectorization of user skills and goals
- Cosine similarity calculation for match scoring
- Automatic matching of learners with relevant mentors
- Match percentage displayed (0-100%)

### 3. Personalized Dashboard
- Role-based view (Mentor vs Learner)
- Top 6 AI-recommended matches
- Skills and goals visualization
- Upcoming session overview

### 4. Mentor Profiles & Session Booking
- Detailed mentor profiles with skills, bio, and availability
- Session booking with date/time picker
- Topic and duration selection (30/60/90 minutes)

### 5. Skill Progress Tracking
- Visual progress bars for each skill
- Interactive Chart.js bar chart
- Manual progress updates (+10% increment)
- Progress history tracking

## Sample Data
The app automatically initializes with sample users:

**Mentors:**
- Sarah Chen (ML/AI expertise)
- David Rodriguez (Full-Stack Development)
- Emily Johnson (UI/UX Design)

**Learners:**
- Alex Kim (Learning web development)
- Maria Garcia (Transitioning to AI/ML)

## Demo Accounts
- **Mentor:** sarah@skillsync.com / mentor123
- **Learner:** alex@example.com / learner123

## Database Schema

### User Model
- Authentication fields (email, password_hash)
- Profile data (name, bio, skills, goals)
- Role flag (is_mentor)
- Availability information

### SkillProgress Model
- User-skill relationship
- Progress level (0.0 - 1.0)
- Last updated timestamp

### MentorSession Model
- Mentor-learner pairing
- Session details (time, duration, topic)
- Status tracking

## Recent Changes
- **Nov 7, 2025:** Initial MVP implementation
  - Complete Flask application with all core features
  - AI matching engine using scikit-learn
  - Beautiful TailwindCSS UI with gradient design
  - Skill progress tracking with Chart.js
  - Sample data initialization
  - **CRITICAL FIX:** Corrected AI matching logic to ensure mentors only see learners and vice versa (removed same-role matching bug)

## User Preferences
- Design preference: Modern, motivating UI with soft gradients and rounded cards
- Technology stack: Flask (Python), TailwindCSS, vanilla JavaScript
- AI approach: Lightweight, CPU-friendly libraries (scikit-learn instead of heavy transformers)

## Next Phase Enhancements
1. **Real-time Chat:** Flask-SocketIO for live mentorship sessions
2. **PostgreSQL Database:** Production-ready persistence
3. **Advanced AI:** Upgrade to sentence-transformers or OpenAI embeddings
4. **AI Chat Assistant:** OpenAI integration for career guidance
5. **Gamification:** Badges and achievement system
6. **Email Notifications:** Session reminders and match alerts
7. **Calendar Integration:** Google Calendar sync for sessions
8. **Video Chat:** WebRTC for virtual mentorship

## Running the Application
The Flask app runs on port 5000 with auto-reload enabled in development mode.
Sample data is automatically initialized on first run.

## Notes
- TailwindCSS is loaded via CDN (development only)
- SQLite database file: `skillsync.db` (auto-created)
- Session secret managed via environment variable SESSION_SECRET
