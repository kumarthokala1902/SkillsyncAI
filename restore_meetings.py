from app import db, LiveMeeting, app, User
import firebase_service as fs_svc
from firebase_config import db_firestore
from datetime import datetime

with app.app_context():
    fs = fs_svc._get_fs()
    if fs:
        col_ref = fs.collection('liveMeetings')
        docs = col_ref.stream()
        restored = 0
        for doc in docs:
            data = doc.to_dict()
            meeting_id = data.get('meetingId')
            if not meeting_id:
                continue
            try:
                mid = int(meeting_id)
            except ValueError:
                continue
                
            existing = LiveMeeting.query.get(mid)
            if not existing:
                creator_id = data.get('creatorId')
                user = User.query.get(creator_id) if creator_id else None
                
                # Parse date
                sch_at = data.get('scheduledAt')
                parsed_date = None
                if sch_at:
                    try:
                        parsed_date = datetime.fromisoformat(sch_at.replace('Z', '+00:00'))
                    except Exception:
                        parsed_date = datetime.utcnow()
                        
                m = LiveMeeting(
                    id=mid,
                    title=data.get('title', 'Restored Meeting'),
                    description=data.get('description', ''),
                    language=data.get('language', 'English'),
                    skill_category=data.get('skillCategory', 'General'),
                    scheduled_at=parsed_date or datetime.utcnow(),
                    duration_minutes=data.get('durationMinutes', 60),
                    meeting_link=data.get('meetingLink', ''),
                    max_participants=data.get('maxParticipants', 50),
                    status=data.get('status', 'scheduled'),
                    creator_id=user.id if user else 1 # Fallback to 1 if not found
                )
                db.session.add(m)
                restored += 1
                
        db.session.commit()
        print(f"Restored {restored} live meetings to local DB.")
    else:
        print("Firebase not configured.")
