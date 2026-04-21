"""
firebase_service.py
────────────────────
Pure-Python service layer for Firestore CRUD + duplicate cleanup.
No Flask imports – call from app.py routes after checking firebase_enabled.

All public functions are safe to call even when firebase_enabled=False;
they simply return early so the main app flow is never interrupted.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Internal helper ──────────────────────────────────────────────────────────

def _get_fs():
    """Return the Firestore client or None."""
    from firebase_config import db_firestore, firebase_enabled
    if not firebase_enabled or db_firestore is None:
        return None
    return db_firestore


# ─── User Sync ────────────────────────────────────────────────────────────────

def sync_user_to_firestore(user) -> bool:
    """
    Upsert a SQLAlchemy User object to Firestore users/{userId}.
    Safe to call on every login/register – uses merge=True (no overwrite).
    """
    fs = _get_fs()
    if fs is None:
        return False
    try:
        doc_ref = fs.collection("users").document(str(user.id))
        doc_ref.set(
            {
                "userId":    str(user.id),
                "name":      user.name,
                "email":     user.email,
                "role":      user.role,
                "isBlocked": getattr(user, "is_blocked", False),
                "isVerified": getattr(user, "is_verified", False),
                "skills":    user.skills,
                "bio":       getattr(user, "bio", ""),
                "collegeCode": getattr(user, "college_code", ""),
                "collegeName": getattr(user, "college_name", ""),
                "createdAt": user.created_at.isoformat() if user.created_at else datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
            merge=True,
        )
        logger.debug("Synced user %s to Firestore", user.id)
        return True
    except Exception as exc:
        logger.error("sync_user_to_firestore error: %s", exc)
        return False


def delete_user_from_firestore(user_id: int) -> bool:
    """Hard-delete a user document from Firestore (admin only)."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        fs.collection("users").document(str(user_id)).delete()
        logger.info("Deleted Firestore user doc %s", user_id)
        return True
    except Exception as exc:
        logger.error("delete_user_from_firestore error: %s", exc)
        return False


def update_user_role_in_firestore(user_id: int, role: str) -> bool:
    """Update only the role field for a user doc."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        from google.cloud.firestore_v1 import SERVER_TIMESTAMP
        fs.collection("users").document(str(user_id)).update(
            {"role": role, "updatedAt": datetime.now(timezone.utc).isoformat()}
        )
        return True
    except Exception as exc:
        logger.error("update_user_role_in_firestore error: %s", exc)
        return False


def block_user_in_firestore(user_id: int, blocked: bool) -> bool:
    """Toggle the isBlocked flag on a user doc."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        fs.collection("users").document(str(user_id)).update(
            {"isBlocked": blocked, "updatedAt": datetime.now(timezone.utc).isoformat()}
        )
        return True
    except Exception as exc:
        logger.error("block_user_in_firestore error: %s", exc)
        return False


# ─── Group Sync ───────────────────────────────────────────────────────────────

def sync_group_to_firestore(group_id: str, title: str, created_by: str, members: list) -> bool:
    """Upsert a study group to Firestore groups/{groupId}."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        fs.collection("groups").document(group_id).set(
            {
                "groupId":   group_id,
                "title":     title,
                "createdBy": created_by,
                "members":   members,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
            merge=True,
        )
        return True
    except Exception as exc:
        logger.error("sync_group_to_firestore error: %s", exc)
        return False


# ─── Message Sync ─────────────────────────────────────────────────────────────

def sync_message_to_firestore(
    message_id: str,
    sender_id: str,
    group_id: str,
    content: str,
) -> bool:
    """Add a message document to Firestore messages/{messageId}."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        fs.collection("messages").document(message_id).set(
            {
                "messageId": message_id,
                "senderId":  sender_id,
                "groupId":   group_id,
                "content":   content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return True
    except Exception as exc:
        logger.error("sync_message_to_firestore error: %s", exc)
        return False


# ─── Event Sync ───────────────────────────────────────────────────────────────

def sync_event_to_firestore(meetup) -> bool:
    """Upsert a Meetup (event) to Firestore events/{eventId}."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        event_id = str(meetup.id)
        participants = []  # Extend when you add an attendees relationship
        fs.collection("events").document(event_id).set(
            {
                "eventId":      event_id,
                "title":        meetup.title,
                "description":  meetup.description,
                "hostId":       str(meetup.organizer_id),
                "location":     meetup.location,
                "dateTime":     meetup.date_time.isoformat() if meetup.date_time else None,
                "participants": participants,
                "updatedAt":    datetime.now(timezone.utc).isoformat(),
            },
            merge=True,
        )
        return True
    except Exception as exc:
        logger.error("sync_event_to_firestore error: %s", exc)
        return False


# ─── Duplicate Cleanup ────────────────────────────────────────────────────────

def _deduplicate_collection(collection_name: str, unique_field: str) -> dict:
    """
    Generic deduplication: for each unique value of `unique_field`,
    keep the document with the latest `updatedAt` / `createdAt`,
    delete the rest.
    Returns a summary dict.
    """
    fs = _get_fs()
    if fs is None:
        return {"error": "Firebase not enabled", "deleted": 0}

    deleted: int = 0
    errors: int = 0
    try:
        docs = list(fs.collection(collection_name).stream())
        grouped: dict = {}
        for doc in docs:
            data = doc.to_dict()
            key = str(data.get(unique_field, ""))
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(doc)

        for _key, doc_list in grouped.items():
            if len(doc_list) <= 1:
                continue

            def _sort_key(d):
                d_data = d.to_dict()
                return d_data.get("updatedAt") or d_data.get("createdAt") or ""

            doc_list.sort(key=_sort_key, reverse=True)
            # Keep index 0 (newest), delete the rest
            for stale_doc in doc_list[1:]:
                try:
                    stale_doc.reference.delete()
                    deleted = deleted + 1
                except Exception as e:
                    logger.error("Failed to delete stale doc %s: %s", stale_doc.id, e)
                    errors = errors + 1

    except Exception as exc:
        logger.error("_deduplicate_collection(%s) error: %s", collection_name, exc)
        return {"error": str(exc), "deleted": deleted}

    return {"collection": collection_name, "deleted": deleted, "errors": errors}


def cleanup_duplicate_users() -> dict:
    return _deduplicate_collection("users", "email")


def cleanup_duplicate_groups() -> dict:
    return _deduplicate_collection("groups", "groupId")


def cleanup_duplicate_events() -> dict:
    return _deduplicate_collection("events", "eventId")


def cleanup_all_duplicates() -> dict:
    """Run deduplication across all collections and return a summary."""
    results = {
        "users":  cleanup_duplicate_users(),
        "groups": cleanup_duplicate_groups(),
        "events": cleanup_duplicate_events(),
    }
    total_deleted = sum(r.get("deleted", 0) for r in results.values())
    results["total_deleted"] = total_deleted
    return results


# ─── Analytics Snapshot ───────────────────────────────────────────────────────

def get_firestore_analytics() -> dict:
    """
    Returns basic counts from Firestore for the admin dashboard.
    Falls back gracefully if Firestore is not enabled.
    """
    fs = _get_fs()
    if fs is None:
        return {"users": 0, "groups": 0, "messages": 0, "events": 0, "firebase_enabled": False}
    try:
        counts = {}
        for col in ("users", "groups", "messages", "events"):
            counts[col] = len(list(fs.collection(col).stream()))
        counts["firebase_enabled"] = True
        return counts
    except Exception as exc:
        logger.error("get_firestore_analytics error: %s", exc)
        return {"users": 0, "groups": 0, "messages": 0, "events": 0, "firebase_enabled": False}


# ─── Learning Modes Data ──────────────────────────────────────────────────────

def get_peer_sessions() -> list:
    """Fetch all peer learning sessions from Firestore. Populates sample if empty."""
    fs = _get_fs()
    if fs is None: return []
    try:
        col_ref = fs.collection("peerSessions")
        docs = list(col_ref.stream())
        if not docs:
            samples = [
                {"id": "p1", "topic": "React Hooks Discussion", "participants": ["User1", "User2"], "status": "active"},
                {"id": "p2", "topic": "DSA Interview Prep", "participants": ["User3"], "status": "active"},
                {"id": "p3", "topic": "Machine Learning Ethics", "participants": ["User4", "User5", "User6"], "status": "active"}
            ]
            for s in samples: col_ref.add(s)
            return samples
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error("get_peer_sessions error: %s", e)
        return []

def get_recordings() -> list:
    """Fetch all recorded sessions from Firestore. Populates sample if empty."""
    fs = _get_fs()
    if fs is None: return []
    try:
        col_ref = fs.collection("recordings")
        docs = list(col_ref.stream())
        if not docs:
            # Populate sample data for demo
            samples = [
                {
                    "id": "rec1",
                    "title": "Mastering Python Generators",
                    "duration": "15:20",
                    "thumbnail": "https://img.youtube.com/vi/D1tFehUshZ0/0.jpg",
                    "url": "https://youtube.com/watch?v=D1tFehUshZ0"
                },
                {
                    "id": "rec2",
                    "title": "Firebase + Flask Integration",
                    "duration": "22:45",
                    "thumbnail": "https://img.youtube.com/vi/W-8_oU6f23M/0.jpg",
                    "url": "https://youtube.com/watch?v=W-8_oU6f23M"
                },
                {
                    "id": "rec3",
                    "title": "Advanced CSS Grid Layouts",
                    "duration": "10:15",
                    "thumbnail": "https://img.youtube.com/vi/7kVeCqQCxlk/0.jpg",
                    "url": "https://youtube.com/watch?v=7kVeCqQCxlk"
                }
            ]
            for s in samples:
                col_ref.add(s)
            return samples
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error("get_recordings error: %s", e)
        return []

def get_live_sessions() -> list:
    """Fetch all live sessions from Firestore. Populates sample if empty."""
    fs = _get_fs()
    if fs is None: return []
    try:
        col_ref = fs.collection("liveSessions")
        docs = list(col_ref.stream())
        if not docs:
            samples = [
                {"id": "l1", "topic": "Morning Sync: Today's Tech News", "time": "10:00 AM", "host": "SkillSync Team"}
            ]
            for s in samples: col_ref.add(s)
            return samples
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error("get_live_sessions error: %s", e)
        return []


def get_upcoming_sessions() -> list:
    """
    Fetch upcoming sessions from Firestore liveSessions collection.
    Returns sessions sorted by time. Falls back to sample data if collection is empty.
    """
    fs = _get_fs()
    if fs is None:
        return [
            {"title": "DevOps Live", "time": "6:00 PM", "type": "Live", "join_url": "#"},
            {"title": "DSA Peer Session", "time": "7:30 PM", "type": "Peer", "join_url": "#"},
            {"title": "Python Basics", "time": "9:00 PM", "type": "Recording", "join_url": "#"},
        ]
    try:
        col_ref = fs.collection("liveSessions")
        docs = list(col_ref.stream())
        sessions = []
        for doc in docs:
            data = doc.to_dict()
            sessions.append({
                "title": data.get("topic", data.get("title", "Session")),
                "time": data.get("time", "TBD"),
                "type": data.get("type", "Live"),
                "join_url": data.get("join_url", data.get("meetingLink", "#")),
            })
        if not sessions:
            return [
                {"title": "DevOps Live", "time": "6:00 PM", "type": "Live", "join_url": "#"},
                {"title": "DSA Peer Session", "time": "7:30 PM", "type": "Peer", "join_url": "#"},
                {"title": "Python Basics", "time": "9:00 PM", "type": "Recording", "join_url": "#"},
            ]
        return sessions
    except Exception as e:
        logger.error("get_upcoming_sessions error: %s", e)
        return []


def get_suggested_peers(exclude_user_id: str, limit: int = 5) -> list:
    """
    Fetch suggested peers from Firestore users collection.
    Excludes the current logged-in user. Returns students and mentors only.
    """
    fs = _get_fs()
    if fs is None: return []
    try:
        col_ref = fs.collection("users")
        docs = list(col_ref.stream())
        peers = []
        for doc in docs:
            data = doc.to_dict()
            if str(data.get("userId", "")) == str(exclude_user_id):
                continue
            role = data.get("role", "student")
            if role not in ("student", "mentor"):
                continue
            skills_raw = data.get("skills", "")
            if isinstance(skills_raw, list):
                skill_label = skills_raw[0] if skills_raw else "SkillSync Learner"
            else:
                parts = [s.strip() for s in str(skills_raw).split(",") if s.strip()]
                skill_label = parts[0] if parts else "SkillSync Learner"
            peers.append({
                "name": data.get("name", "Unknown"),
                "skill": skill_label,
                "role": role,
                "user_id": data.get("userId", ""),
                "initial": (data.get("name", "?")[0]).upper(),
            })
        return peers[:limit]
    except Exception as e:
        logger.error("get_suggested_peers error: %s", e)
        return []


# ─── Live Meeting Sync ────────────────────────────────────────────────────────

def sync_meeting_to_firestore(meeting) -> bool:
    """
    Upsert a LiveMeeting object to Firestore liveMeetings/{meetingId}.
    Called on create and update so clients get real-time status changes.
    """
    fs = _get_fs()
    if fs is None:
        return False
    try:
        doc_ref = fs.collection("liveMeetings").document(str(meeting.id))
        doc_ref.set(
            {
                "meetingId":       str(meeting.id),
                "title":           meeting.title,
                "description":     getattr(meeting, "description", "") or "",
                "language":        meeting.language,
                "skillCategory":   meeting.skill_category,
                "scheduledAt":     meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
                "durationMinutes": meeting.duration_minutes,
                "meetingLink":     meeting.meeting_link or "",
                "maxParticipants": meeting.max_participants,
                "participantCount": len(meeting.participants) if hasattr(meeting, "participants") else 0,
                "status":          meeting.status,
                "creatorId":       str(meeting.creator_id),
                "creatorName":     meeting.creator.name if meeting.creator else "",
                "updatedAt":       datetime.now(timezone.utc).isoformat(),
            },
            merge=True,
        )
        logger.debug("Synced LiveMeeting %s to Firestore", meeting.id)
        return True
    except Exception as exc:
        logger.error("sync_meeting_to_firestore error: %s", exc)
        return False


def update_meeting_status_in_firestore(meeting_id: int, status: str, participant_count: int = 0) -> bool:
    """Lightweight status-only update — used during auto-status flips."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        fs.collection("liveMeetings").document(str(meeting_id)).update(
            {
                "status":          status,
                "participantCount": participant_count,
                "updatedAt":       datetime.now(timezone.utc).isoformat(),
            }
        )
        return True
    except Exception as exc:
        logger.error("update_meeting_status_in_firestore error: %s", exc)
        return False


def delete_meeting_from_firestore(meeting_id: int) -> bool:
    """Hard-delete a meeting document from Firestore."""
    fs = _get_fs()
    if fs is None:
        return False
    try:
        fs.collection("liveMeetings").document(str(meeting_id)).delete()
        logger.info("Deleted Firestore liveMeeting doc %s", meeting_id)
        return True
    except Exception as exc:
        logger.error("delete_meeting_from_firestore error: %s", exc)
        return False

def sync_booking_to_firestore(booking) -> bool:
    """
    Upsert a MentorBooking object to Firestore mentor_bookings/{bookingId}.
    This mirrors the SQL state to Firestore for real-time messaging locks and dashboards.
    """
    fs = _get_fs()
    if fs is None:
        return False
    try:
        from datetime import datetime, timezone
        doc_ref = fs.collection("mentor_bookings").document(str(booking.id))
        
        # Calculate window
        start_dt = datetime.combine(booking.date, booking.time)
        end_dt = start_dt + __import__('datetime').timedelta(minutes=booking.duration)
        
        doc_ref.set(
            {
                "bookingId":   str(booking.id),
                "mentorId":    str(booking.mentor_id),
                "studentId":   str(booking.student_id),
                "mentorName":  booking.mentor.name if booking.mentor else "Mentor",
                "studentName": booking.student.name if booking.student else "Student",
                "topic":       booking.topic,
                "status":      booking.status,
                "mode":        booking.mode,
                "scheduledAt": start_dt.isoformat(),
                "expiresAt":   end_dt.isoformat(),
                "meetingLink": booking.meeting_link or "",
                "updatedAt":   datetime.now(timezone.utc).isoformat(),
                "isChatLocked": booking.status != 'accepted'
            },
            merge=True,
        )
        logger.debug("Synced MentorBooking %s to Firestore", booking.id)
        return True
    except Exception as exc:
        logger.error("sync_booking_to_firestore error: %s", exc)
        return False
