"""Firestore-backed application models.

Existing route-facing model/query APIs are preserved while Firestore is the
only persistence layer. No relational database or ORM is used here.
"""
from __future__ import annotations

import json
import random
import time
from datetime import date, datetime, time, timedelta
from typing import Callable

from flask_login import UserMixin


def _next_id():
    return int(time.time() * 1000000) + random.randint(0, 999)


class _Condition:
    def __init__(self, predicate: Callable):
        self.predicate = predicate

    def __call__(self, item):
        try:
            return bool(self.predicate(item))
        except (AttributeError, TypeError, ValueError):
            return False

    def __and__(self, other):
        return _Condition(lambda item: self(item) and other(item))

    def __or__(self, other):
        return _Condition(lambda item: self(item) or other(item))


class _Field:
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner):
        return self if instance is None else instance._data.get(self.name)

    def __set__(self, instance, value):
        instance._data[self.name] = value

    def _compare(self, operation, other):
        return _Condition(lambda item: operation(getattr(item, self.name, None), other))

    def __eq__(self, other): return self._compare(lambda a, b: a == b, other)
    def __ne__(self, other): return self._compare(lambda a, b: a != b, other)
    def __lt__(self, other): return self._compare(lambda a, b: a is not None and a < b, other)
    def __le__(self, other): return self._compare(lambda a, b: a is not None and a <= b, other)
    def __gt__(self, other): return self._compare(lambda a, b: a is not None and a > b, other)
    def __ge__(self, other): return self._compare(lambda a, b: a is not None and a >= b, other)
    def contains(self, value): return _Condition(lambda item: value in (getattr(item, self.name, "") or ""))
    def in_(self, values): return _Condition(lambda item: getattr(item, self.name, None) in values)
    def asc(self): return _Order(self.name, False)
    def desc(self): return _Order(self.name, True)


class _Order:
    def __init__(self, field, reverse):
        self.field = field
        self.reverse = reverse


class _RandomOrder:
    field = ""
    reverse = False


class _Page:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, (total + per_page - 1) // per_page)
        self.has_next = page < self.pages
        self.has_prev = page > 1


class _Query:
    def __init__(self, model, conditions=None, orders=None, max_items=None):
        self.model = model
        self.conditions = conditions or []
        self.orders = orders or []
        self.max_items = max_items

    def _items(self):
        items = self.model._load_all()
        for condition in self.conditions:
            items = [item for item in items if condition(item)]
        for order in reversed(self.orders):
            if isinstance(order, _RandomOrder):
                random.shuffle(items)
            else:
                items.sort(key=lambda item: getattr(item, order.field, None) or "", reverse=order.reverse)
        return items[:self.max_items] if self.max_items is not None else items

    def filter(self, *conditions): return _Query(self.model, self.conditions + list(conditions), self.orders, self.max_items)
    def filter_by(self, **values):
        return self.filter(*[_Condition(lambda item, key=k, value=v: getattr(item, key, None) == value) for k, v in values.items()])
    def order_by(self, *orders): return _Query(self.model, self.conditions, self.orders + list(orders), self.max_items)
    def limit(self, amount): return _Query(self.model, self.conditions, self.orders, amount)
    def all(self): return self._items()
    def first(self):
        items = self.limit(1)._items()
        return items[0] if items else None
    def first_or_404(self):
        item = self.first()
        if item is None:
            from flask import abort
            abort(404)
        return item
    def get(self, identifier):
        return self.filter(_Condition(lambda item: str(getattr(item, "id", "")) == str(identifier))).first()
    def get_or_404(self, identifier):
        item = self.get(identifier)
        if item is None:
            from flask import abort
            abort(404)
        return item
    def count(self): return len(self._items())
    def paginate(self, page=1, per_page=20, error_out=False):
        if page < 1:
            if error_out:
                from flask import abort
                abort(404)
            page = 1
        items = self._items()
        start = (page - 1) * per_page
        return _Page(items[start:start + per_page], page, per_page, len(items))
    def delete(self):
        items = self._items()
        for item in items: db.session.delete(item)
        return len(items)
    def update(self, values):
        items = self._items()
        for item in items:
            for key, value in values.items(): setattr(item, key, value)
            db.session.track(item)
        return len(items)


class _QueryDescriptor:
    def __get__(self, instance, owner): return _Query(owner)


class _Session:
    def __init__(self):
        self.pending = []
        self.deleted = []
        self.tracked = {}

    def add(self, item):
        if item not in self.pending: self.pending.append(item)
        return item

    def track(self, item):
        self.tracked[(item.__class__, str(item.id))] = item
        return item

    def delete(self, item):
        if item not in self.deleted: self.deleted.append(item)

    def flush(self):
        for item in self.pending: item._ensure_id()

    def commit(self):
        self.flush()
        for item in self.pending + list(self.tracked.values()):
            if item not in self.deleted: item._save()
        for item in self.deleted: item._delete()
        self.pending.clear(); self.deleted.clear()

    def remove(self):
        self.pending.clear(); self.deleted.clear(); self.tracked.clear()

    def rollback(self):
        self.pending.clear(); self.deleted.clear()


class _Functions:
    @staticmethod
    def random(): return _RandomOrder()


class _FirestoreStore:
    func = _Functions()

    def __init__(self): self.session = _Session()
    def init_app(self, app): return None
    @staticmethod
    def or_(*conditions): return _Condition(lambda item: any(condition(item) for condition in conditions))
    @staticmethod
    def and_(*conditions): return _Condition(lambda item: all(condition(item) for condition in conditions))
    @staticmethod
    def extract(part, field):
        return _Condition(lambda item: getattr(item, field.name, None).year == part if part == "year" else getattr(item, field.name, None).month == part)


db = _FirestoreStore()


class FirestoreModel:
    query = _QueryDescriptor()
    _collection = None

    def __init__(self, **values):
        self._data = {}
        for key, value in values.items():
            if isinstance(value, str) and key in {"date", "last_active_date"}:
                try: value = date.fromisoformat(value)
                except ValueError: pass
            elif isinstance(value, str) and key == "time":
                try: value = time.fromisoformat(value)
                except ValueError: pass
            elif isinstance(value, str) and key in {"created_at", "updated_at", "scheduled_time", "scheduled_at", "start_time", "end_time", "submitted_at", "reviewed_at", "applied_at", "joined_at", "completed_at", "expires_at"}:
                try: value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError: pass
            setattr(self, key, value)
        self._ensure_id()

    def _ensure_id(self):
        if not self._data.get("id"): self._data["id"] = _next_id()

    @classmethod
    def _firestore(cls):
        from firebase_config import db_firestore
        return db_firestore

    @classmethod
    def _load_all(cls):
        fs = cls._firestore()
        if fs is None: return []
        try:
            result = []
            for doc in fs.collection(cls._collection).stream():
                values = doc.to_dict()
                values.setdefault("id", doc.id)
                item = cls(**values)
                db.session.track(item)
                result.append(item)
            return result
        except Exception:
            return []

    def _save(self):
        fs = self._firestore()
        if fs is None: return
        data = {}
        for key, value in self._data.items():
            if key.startswith("_"): continue
            if isinstance(value, (date, time)) and not isinstance(value, datetime): value = value.isoformat()
            data[key] = value
        fs.collection(self._collection).document(str(self.id)).set(data, merge=True)

    def _delete(self):
        fs = self._firestore()
        if fs is not None: fs.collection(self._collection).document(str(self.id)).delete()

    def __repr__(self): return f"<{self.__class__.__name__} {getattr(self, 'id', '')}>"


def _define_fields(cls, fields):
    for field in fields: setattr(cls, field, _Field(field))
    return cls


def _related(model, foreign_key, many=True):
    def getter(self):
        query = model.query.filter_by(**{foreign_key: self.id})
        return query.all() if many else query.first()
    return property(getter)


class User(UserMixin, FirestoreModel):
    _collection = "users"
    def get_skills_list(self): return [item.strip() for item in str(self.skills or "").split(",") if item.strip()]
    def get_goals_list(self): return [item.strip() for item in str(self.goals or "").split(",") if item.strip()]
    @property
    def connection_count(self):
        return len([item for item in self.sent_connections + self.received_connections if item.status in ("Accepted", "Completed")])


class SkillProgress(FirestoreModel):
    _collection = "skill_progress"
    def update_progress(self, increment=0.1):
        self.level = min(1.0, (self.level or 0) + increment); self.last_updated = datetime.utcnow()


class MentorBooking(FirestoreModel):
    _collection = "mentor_bookings"
    @property
    def start_datetime(self): return datetime.combine(self.date, self.time)
    @property
    def end_datetime(self): return self.start_datetime + timedelta(minutes=self.duration)
    def to_dict(self): return {key: value for key, value in self._data.items() if not key.startswith("_")}


class Poll(FirestoreModel):
    _collection = "polls"
    def get_options_list(self): return [item.strip() for item in str(self.options or "").split(";") if item.strip()]
    def get_votes_list(self): return [int(item) for item in str(self.votes or "").split(";") if item.strip()] or [0] * len(self.get_options_list())
    def set_votes_list(self, values): self.votes = ";".join(map(str, values))


class AIMessage(FirestoreModel):
    _collection = "ai_messages"
    def get_metadata(self):
        try: return json.loads(self.metadata_json or "{}")
        except (TypeError, ValueError): return {}
    def set_metadata(self, data): self.metadata_json = json.dumps(data)


class LearningPath(FirestoreModel):
    _collection = "learning_paths"
    def get_milestones(self):
        try: return json.loads(self.milestones_json or "[]")
        except (TypeError, ValueError): return []
    def set_milestones(self, milestones): self.milestones_json = json.dumps(milestones)


class MockInterview(FirestoreModel):
    _collection = "mock_interviews"
    def _json_list(self, field):
        try: return json.loads(getattr(self, field) or "[]")
        except (TypeError, ValueError): return []
    def get_questions(self): return self._json_list("questions_json")
    def get_answers(self): return self._json_list("answers_json")
    def get_scores(self): return self._json_list("scores_json")
    def get_feedback(self): return self._json_list("feedback_json")


class CourseProgress(FirestoreModel):
    _collection = "course_progress"
    def get_completed_videos(self):
        try: return json.loads(self.completed_videos_json or "[]")
        except (TypeError, ValueError): return []
    def set_completed_videos(self, ids): self.completed_videos_json = json.dumps(ids)


class Course(FirestoreModel):
    _collection = "courses"
    def get_videos(self):
        try: return json.loads(self.videos_json or "[]")
        except (TypeError, ValueError): return []
    def set_videos(self, videos): self.videos_json = json.dumps(videos)


class SkillQuestion(FirestoreModel):
    _collection = "skill_questions"
    def get_options(self):
        try: return json.loads(self.options_json or "[]")
        except (TypeError, ValueError): return []


class LiveMeeting(FirestoreModel):
    _collection = "live_meetings"
    @property
    def participant_count(self): return len(self.participants)
    @property
    def is_full(self): return self.participant_count >= self.max_participants
    def auto_update_status(self):
        now = datetime.utcnow(); end_time = self.scheduled_at + timedelta(minutes=self.duration_minutes)
        self.status = "completed" if now >= end_time else "live" if now >= self.scheduled_at else "upcoming"
    def to_dict(self): return {key: value for key, value in self._data.items() if not key.startswith("_")}


class SkillTest(FirestoreModel):
    _collection = "skill_tests"
    def get_questions(self):
        try: return json.loads(self.questions_json or "[]")
        except (TypeError, ValueError): return []
    def set_questions(self, questions): self.questions_json = json.dumps(questions)


_MODEL_NAMES = [
    "MentorSession", "MentorBookingMeeting", "Post", "PostLike", "PostSave", "PostView", "PostComment",
    "Meetup", "MeetupRSVP", "Career", "CodingChallenge", "ChallengeSubmission", "GamificationProfile", "Group",
    "GroupMember", "CareerApplication", "PeerConnection", "PeerRequest", "PeerSession", "Notification", "AIConversation",
    "CourseCategory", "VerificationRequest", "MeetingParticipant", "TestResult", "MentorFeedback",
]
_COLLECTIONS = {
    "MentorSession": "mentor_sessions", "MentorBookingMeeting": "mentor_booking_meetings", "Post": "posts", "PostLike": "post_likes", "PostSave": "post_saves", "PostView": "post_views", "PostComment": "post_comments", "Meetup": "meetups", "MeetupRSVP": "meetup_rsvps", "Career": "careers", "CodingChallenge": "coding_challenges", "ChallengeSubmission": "challenge_submissions", "GamificationProfile": "gamification_profiles", "Group": "groups", "GroupMember": "group_members", "CareerApplication": "career_applications", "PeerConnection": "peer_connections", "PeerRequest": "peer_requests", "PeerSession": "peer_sessions", "Notification": "notifications", "AIConversation": "ai_conversations", "CourseCategory": "course_categories", "VerificationRequest": "verification_requests", "MeetingParticipant": "meeting_participants", "TestResult": "test_results", "MentorFeedback": "mentor_feedback",
}
for _name in _MODEL_NAMES: globals()[_name] = type(_name, (FirestoreModel,), {"_collection": _COLLECTIONS[_name]})


_FIELDS = {
    "User": "id name email skills goals bio is_mentor role is_blocked education_level college_code college_name learning_mode expertise years_experience job_role is_verified verified_skill verified_role verification_status availability created_at firebase_uid".split(),
    "SkillProgress": "id user_id skill_name level last_updated".split(), "MentorSession": "id mentor_id learner_id scheduled_time duration_minutes topic status meet_link created_at updated_at notes feedback".split(), "MentorBooking": "id mentor_id student_id topic date time duration mode status meeting_link message reject_reason created_at updated_at".split(), "MentorBookingMeeting": "id booking_id room_id meeting_link start_time end_time status created_at".split(),
    "Post": "id user_id content link created_at share_count views_count".split(), "Poll": "id post_id question options votes".split(), "PostLike": "id post_id user_id created_at".split(), "PostSave": "id post_id user_id created_at".split(), "PostView": "id post_id user_id created_at".split(), "PostComment": "id post_id user_id content created_at".split(), "Meetup": "id title description date_time location organizer_id max_participants banner_url created_at".split(), "MeetupRSVP": "id meetup_id user_id status created_at".split(),
    "Career": "id title company location job_type description requirements salary_range posted_by_id created_at".split(), "CodingChallenge": "id title description difficulty base_code points_reward xp_reward is_active posted_by_id created_at".split(), "ChallengeSubmission": "id challenge_id user_id submitted_code language time_taken_seconds status admin_feedback submitted_at reviewed_at reviewed_by_id".split(), "GamificationProfile": "id user_id coins xp streak_days last_active_date".split(), "Group": "id name description category location mode banner_url creator_id created_at".split(), "GroupMember": "id group_id user_id joined_at".split(), "CareerApplication": "id career_id user_id status resume_url applied_at".split(),
    "PeerConnection": "id sender_id receiver_id status topic scheduled_at meeting_id rating feedback created_at expires_at zoom_url zoom_meeting_id".split(), "PeerRequest": "id sender_id receiver_id skills_expected skills_offered peer_mode date time duration message status created_at".split(), "PeerSession": "id user_a_id user_b_id session_type start_time end_time status video_link associated_request_id".split(), "Notification": "id user_id title message type link is_read created_at".split(), "AIConversation": "id user_id title created_at updated_at".split(), "AIMessage": "id conversation_id role content context_type confidence metadata_json created_at".split(), "LearningPath": "id user_id goal milestones_json current_milestone completion_pct created_at updated_at".split(), "MockInterview": "id user_id interview_type questions_json answers_json scores_json feedback_json overall_score current_question is_complete created_at".split(), "CourseProgress": "id user_id playlist_id completed_videos_json last_video_id updated_at".split(), "CourseCategory": "id name created_at".split(), "Course": "id title instructor thumbnail playlist_id playlist_link category_id videos_json created_at".split(), "SkillQuestion": "id category type question_text options_json correct_answer base_code difficulty".split(), "VerificationRequest": "id user_id role language mcq_answers_json coding_answers_json score status submitted_at reviewed_at reviewed_by reviewer_notes".split(), "LiveMeeting": "id title description language skill_category scheduled_at duration_minutes meeting_link max_participants status creator_id created_at updated_at".split(), "MeetingParticipant": "id meeting_id user_id joined_at".split(), "SkillTest": "id title skill_category description questions_json pass_score time_limit_minutes is_active creator_id created_at".split(), "TestResult": "id test_id user_id score passed answers_json completed_at".split(), "MentorFeedback": "id mentor_id student_id rating comment session_id created_at".split(),
}
for _name, _fields in _FIELDS.items(): _define_fields(globals()[_name], _fields)


_RELATIONS = {
    ("User", "skill_progress"): (SkillProgress, "user_id", True), ("User", "sessions_mentoring"): (MentorSession, "mentor_id", True), ("User", "sessions_learning"): (MentorSession, "learner_id", True), ("User", "careers"): (Career, "posted_by_id", True), ("User", "challenges_posted"): (CodingChallenge, "posted_by_id", True), ("User", "challenge_submissions"): (ChallengeSubmission, "user_id", True), ("User", "course_progress"): (CourseProgress, "user_id", True), ("User", "sent_connections"): (PeerConnection, "sender_id", True), ("User", "received_connections"): (PeerConnection, "receiver_id", True), ("User", "received_bookings"): (MentorBooking, "mentor_id", True), ("User", "sent_bookings"): (MentorBooking, "student_id", True), ("User", "notifications"): (Notification, "user_id", True), ("User", "posts"): (Post, "user_id", True), ("User", "likes"): (PostLike, "user_id", True), ("User", "saves"): (PostSave, "user_id", True),
    ("Post", "author"): (User, "user_id", False), ("Post", "poll"): (Poll, "post_id", False), ("Post", "likes"): (PostLike, "post_id", True), ("Post", "comments"): (PostComment, "post_id", True), ("Post", "saves"): (PostSave, "post_id", True), ("Post", "views"): (PostView, "post_id", True), ("PostComment", "author"): (User, "user_id", False), ("PostLike", "user"): (User, "user_id", False), ("PostSave", "user"): (User, "user_id", False), ("PostView", "user"): (User, "user_id", False),
    ("MentorBooking", "mentor"): (User, "mentor_id", False), ("MentorBooking", "student"): (User, "student_id", False), ("MentorBooking", "meeting"): (MentorBookingMeeting, "booking_id", False), ("ChallengeSubmission", "challenge"): (CodingChallenge, "challenge_id", False), ("ChallengeSubmission", "user_submitted"): (User, "user_id", False), ("GamificationProfile", "user"): (User, "user_id", False), ("Group", "creator"): (User, "creator_id", False), ("Group", "members"): (GroupMember, "group_id", True), ("Career", "poster"): (User, "posted_by_id", False), ("Career", "applications"): (CareerApplication, "career_id", True), ("CareerApplication", "career"): (Career, "career_id", False), ("CareerApplication", "user"): (User, "user_id", False), ("PeerConnection", "sender"): (User, "sender_id", False), ("PeerConnection", "receiver"): (User, "receiver_id", False), ("PeerRequest", "sender"): (User, "sender_id", False), ("PeerRequest", "receiver"): (User, "receiver_id", False), ("PeerSession", "user_a"): (User, "user_a_id", False), ("PeerSession", "user_b"): (User, "user_b_id", False), ("AIConversation", "messages"): (AIMessage, "conversation_id", True), ("Course", "category"): (CourseCategory, "category_id", False), ("VerificationRequest", "user"): (User, "user_id", False), ("VerificationRequest", "reviewer"): (User, "reviewed_by", False), ("LiveMeeting", "creator"): (User, "creator_id", False), ("LiveMeeting", "participants"): (MeetingParticipant, "meeting_id", True), ("MeetingParticipant", "user"): (User, "user_id", False), ("SkillTest", "creator"): (User, "creator_id", False), ("SkillTest", "results"): (TestResult, "test_id", True), ("TestResult", "user"): (User, "user_id", False), ("TestResult", "test"): (SkillTest, "test_id", False), ("MentorFeedback", "mentor"): (User, "mentor_id", False), ("MentorFeedback", "student"): (User, "student_id", False),
}
for (_owner, _name), (_model, _foreign_key, _many) in _RELATIONS.items(): setattr(globals()[_owner], _name, _related(_model, _foreign_key, _many))
