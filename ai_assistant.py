"""
SkillSync AI Assistant — FAANG-level Career Intelligence Engine
==============================================================
Fully self-contained, data-driven AI system that acts as:
  • Career Mentor
  • Profile Analyzer
  • Job Match Engine
  • Learning Path Generator
  • Mock Interview Simulator
  • Connection Recommender
  • Weekly Insights Generator

No external API keys required.  All intelligence is computed from
the application's own database and curated knowledge graphs.
"""

from datetime import datetime, timedelta
import json, re, math, random

# ──────────────────────────── Knowledge Graphs ────────────────────────────

SKILL_TREE = {
    # Web Dev
    "HTML": {"level": 1, "domain": "Web Development", "prereqs": []},
    "CSS": {"level": 1, "domain": "Web Development", "prereqs": []},
    "JavaScript": {"level": 2, "domain": "Web Development", "prereqs": ["HTML", "CSS"]},
    "TypeScript": {"level": 3, "domain": "Web Development", "prereqs": ["JavaScript"]},
    "React": {"level": 3, "domain": "Web Development", "prereqs": ["JavaScript"]},
    "Angular": {"level": 3, "domain": "Web Development", "prereqs": ["TypeScript"]},
    "Vue.js": {"level": 3, "domain": "Web Development", "prereqs": ["JavaScript"]},
    "Next.js": {"level": 4, "domain": "Web Development", "prereqs": ["React"]},
    "Node.js": {"level": 3, "domain": "Web Development", "prereqs": ["JavaScript"]},
    "Express": {"level": 3, "domain": "Web Development", "prereqs": ["Node.js"]},
    "REST API": {"level": 3, "domain": "Web Development", "prereqs": ["JavaScript"]},
    "GraphQL": {"level": 4, "domain": "Web Development", "prereqs": ["JavaScript"]},
    "Tailwind CSS": {"level": 2, "domain": "Web Development", "prereqs": ["CSS"]},

    # Backend / Systems
    "Python": {"level": 1, "domain": "Backend", "prereqs": []},
    "Java": {"level": 2, "domain": "Backend", "prereqs": []},
    "C++": {"level": 2, "domain": "Backend", "prereqs": []},
    "Go": {"level": 3, "domain": "Backend", "prereqs": []},
    "Rust": {"level": 4, "domain": "Backend", "prereqs": []},
    "Flask": {"level": 3, "domain": "Backend", "prereqs": ["Python"]},
    "Django": {"level": 3, "domain": "Backend", "prereqs": ["Python"]},
    "Spring Boot": {"level": 3, "domain": "Backend", "prereqs": ["Java"]},
    "FastAPI": {"level": 3, "domain": "Backend", "prereqs": ["Python"]},

    # Data / AI
    "Data Science": {"level": 3, "domain": "Data & AI", "prereqs": ["Python", "Statistics"]},
    "Machine Learning": {"level": 4, "domain": "Data & AI", "prereqs": ["Python", "Statistics"]},
    "Deep Learning": {"level": 5, "domain": "Data & AI", "prereqs": ["Machine Learning"]},
    "NLP": {"level": 5, "domain": "Data & AI", "prereqs": ["Machine Learning"]},
    "Computer Vision": {"level": 5, "domain": "Data & AI", "prereqs": ["Deep Learning"]},
    "TensorFlow": {"level": 4, "domain": "Data & AI", "prereqs": ["Machine Learning"]},
    "PyTorch": {"level": 4, "domain": "Data & AI", "prereqs": ["Machine Learning"]},
    "Statistics": {"level": 2, "domain": "Data & AI", "prereqs": []},
    "Pandas": {"level": 2, "domain": "Data & AI", "prereqs": ["Python"]},
    "NumPy": {"level": 2, "domain": "Data & AI", "prereqs": ["Python"]},

    # DevOps / Cloud
    "Docker": {"level": 3, "domain": "DevOps", "prereqs": []},
    "Kubernetes": {"level": 4, "domain": "DevOps", "prereqs": ["Docker"]},
    "AWS": {"level": 3, "domain": "Cloud", "prereqs": []},
    "Azure": {"level": 3, "domain": "Cloud", "prereqs": []},
    "GCP": {"level": 3, "domain": "Cloud", "prereqs": []},
    "CI/CD": {"level": 3, "domain": "DevOps", "prereqs": []},
    "Terraform": {"level": 4, "domain": "DevOps", "prereqs": []},
    "Linux": {"level": 2, "domain": "DevOps", "prereqs": []},

    # Databases
    "SQL": {"level": 2, "domain": "Database", "prereqs": []},
    "PostgreSQL": {"level": 3, "domain": "Database", "prereqs": ["SQL"]},
    "MongoDB": {"level": 3, "domain": "Database", "prereqs": []},
    "Redis": {"level": 3, "domain": "Database", "prereqs": []},
    "Database Design": {"level": 3, "domain": "Database", "prereqs": ["SQL"]},

    # Design
    "UI/UX Design": {"level": 2, "domain": "Design", "prereqs": []},
    "Figma": {"level": 2, "domain": "Design", "prereqs": []},
    "Product Design": {"level": 3, "domain": "Design", "prereqs": ["UI/UX Design"]},
    "User Research": {"level": 3, "domain": "Design", "prereqs": []},

    # Soft/General
    "System Design": {"level": 5, "domain": "Architecture", "prereqs": []},
    "Microservices": {"level": 4, "domain": "Architecture", "prereqs": ["REST API"]},
    "Cloud Computing": {"level": 3, "domain": "Cloud", "prereqs": []},
    "Data Analysis": {"level": 2, "domain": "Data & AI", "prereqs": ["Statistics"]},
    "Digital Marketing": {"level": 2, "domain": "Marketing", "prereqs": []},
    "SEO": {"level": 2, "domain": "Marketing", "prereqs": []},
    "Content Strategy": {"level": 2, "domain": "Marketing", "prereqs": []},
    "Growth Marketing": {"level": 3, "domain": "Marketing", "prereqs": ["Digital Marketing"]},
    "Product Management": {"level": 3, "domain": "Business", "prereqs": []},
    "Full-Stack Development": {"level": 4, "domain": "Web Development", "prereqs": ["JavaScript", "Node.js"]},
}

ROLE_SKILL_MAP = {
    "frontend developer": ["HTML", "CSS", "JavaScript", "React", "TypeScript", "Tailwind CSS", "REST API", "Git"],
    "backend developer": ["Python", "Java", "Node.js", "SQL", "REST API", "Docker", "Git", "Database Design"],
    "full stack developer": ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "Docker", "REST API", "Git"],
    "data scientist": ["Python", "Statistics", "Machine Learning", "Pandas", "NumPy", "SQL", "Data Science"],
    "ml engineer": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Docker", "AWS"],
    "devops engineer": ["Docker", "Kubernetes", "AWS", "CI/CD", "Terraform", "Linux", "Python"],
    "cloud engineer": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Linux"],
    "ui/ux designer": ["UI/UX Design", "Figma", "Product Design", "User Research", "HTML", "CSS"],
    "product manager": ["Product Management", "Data Analysis", "UI/UX Design", "User Research"],
    "mobile developer": ["JavaScript", "React", "TypeScript", "REST API", "SQL"],
    "system architect": ["System Design", "Microservices", "Docker", "Kubernetes", "Cloud Computing", "SQL"],
}

INTERVIEW_BANK = {
    "technical": [
        {"q": "Explain the difference between a stack and a queue. When would you use each?", "keywords": ["fifo", "lifo", "stack", "queue", "push", "pop", "enqueue", "dequeue", "last in first out", "first in first out"], "topic": "Data Structures"},
        {"q": "What is the time complexity of searching in a binary search tree? What about worst case?", "keywords": ["o(log n)", "o(n)", "balanced", "unbalanced", "skewed", "logarithmic", "binary search"], "topic": "Algorithms"},
        {"q": "Explain the concept of RESTful APIs. What makes an API RESTful?", "keywords": ["stateless", "http", "get", "post", "put", "delete", "resource", "endpoint", "crud", "rest"], "topic": "Web Development"},
        {"q": "What is a database index and how does it improve performance?", "keywords": ["index", "b-tree", "lookup", "performance", "query", "speed", "search", "column", "key"], "topic": "Databases"},
        {"q": "Explain the difference between SQL and NoSQL databases. Give use cases for each.", "keywords": ["relational", "document", "schema", "flexible", "acid", "scale", "sql", "nosql", "mongodb", "postgres"], "topic": "Databases"},
        {"q": "What is Docker and why is it useful in software development?", "keywords": ["container", "image", "isolation", "deploy", "environment", "consistent", "lightweight", "virtual"], "topic": "DevOps"},
        {"q": "Explain the concept of Object-Oriented Programming. Name its four pillars.", "keywords": ["encapsulation", "inheritance", "polymorphism", "abstraction", "class", "object", "oop"], "topic": "Programming"},
        {"q": "What is version control? Explain the Git workflow you follow.", "keywords": ["git", "branch", "commit", "merge", "pull request", "clone", "push", "version", "repository"], "topic": "Tools"},
        {"q": "Explain the MVC architecture pattern. Why is it popular?", "keywords": ["model", "view", "controller", "separation", "concern", "pattern", "architecture", "mvc"], "topic": "Architecture"},
        {"q": "What are microservices? How do they differ from monolithic architecture?", "keywords": ["microservice", "monolith", "independent", "deploy", "scale", "service", "api", "distributed"], "topic": "Architecture"},
        {"q": "Explain how HTTPS works. What is SSL/TLS?", "keywords": ["encrypt", "certificate", "ssl", "tls", "handshake", "public key", "private key", "secure", "https"], "topic": "Security"},
        {"q": "What is caching? Describe different caching strategies.", "keywords": ["cache", "redis", "memory", "ttl", "invalidation", "hit", "miss", "lru", "performance"], "topic": "Performance"},
    ],
    "behavioral": [
        {"q": "Tell me about a time you faced a difficult technical challenge. How did you overcome it?", "keywords": ["challenge", "solution", "approach", "debug", "research", "team", "learn", "systematic", "resolved"], "topic": "Problem Solving"},
        {"q": "Describe a situation where you had to work with a difficult team member.", "keywords": ["communication", "empathy", "conflict", "resolution", "listen", "perspective", "compromise", "team"], "topic": "Teamwork"},
        {"q": "Tell me about a project you're most proud of. What was your role?", "keywords": ["project", "impact", "contribution", "result", "built", "designed", "led", "outcome", "achievement"], "topic": "Achievement"},
        {"q": "How do you prioritize tasks when you have multiple deadlines?", "keywords": ["priority", "deadline", "organize", "urgent", "important", "plan", "schedule", "manage", "time"], "topic": "Time Management"},
        {"q": "Describe a time when you had to learn a new technology quickly.", "keywords": ["learn", "adapt", "study", "documentation", "practice", "tutorial", "course", "quick", "ramp"], "topic": "Learning"},
        {"q": "Tell me about a time you received critical feedback. How did you handle it?", "keywords": ["feedback", "improve", "accept", "growth", "change", "constructive", "reflect", "action"], "topic": "Growth Mindset"},
        {"q": "How do you stay updated with the latest technologies and trends?", "keywords": ["blog", "course", "community", "conference", "newsletter", "github", "read", "practice", "follow"], "topic": "Continuous Learning"},
        {"q": "Describe a situation where you had to explain a complex technical concept to a non-technical person.", "keywords": ["simplify", "analogy", "explain", "non-technical", "clear", "understand", "translate", "communicate"], "topic": "Communication"},
    ],
}

LEARNING_RESOURCES = {
    "HTML": ["freeCodeCamp HTML Course", "MDN Web Docs", "HTML & CSS by Jon Duckett"],
    "CSS": ["CSS Tricks", "freeCodeCamp CSS", "Flexbox Froggy"],
    "JavaScript": ["JavaScript.info", "Eloquent JavaScript", "freeCodeCamp JS"],
    "TypeScript": ["TypeScript Handbook", "Scrimba TypeScript Course"],
    "React": ["React.dev Official Docs", "Scrimba React Course", "Full Stack Open"],
    "Python": ["Python.org Docs", "Automate the Boring Stuff", "CS50 Python"],
    "Machine Learning": ["Andrew Ng's ML Course", "Fast.ai", "Kaggle Learn"],
    "Deep Learning": ["Deep Learning Specialization (Coursera)", "Fast.ai", "PyTorch Tutorials"],
    "Docker": ["Docker Official Docs", "Docker Mastery (Udemy)", "Play with Docker"],
    "Kubernetes": ["Kubernetes.io Docs", "KodeKloud", "CKAD Course"],
    "SQL": ["SQLZoo", "Mode SQL Tutorial", "LeetCode SQL"],
    "AWS": ["AWS Free Tier Labs", "A Cloud Guru", "AWS Skill Builder"],
    "System Design": ["System Design Primer (GitHub)", "Grokking System Design", "ByteByteGo"],
    "Node.js": ["Node.js Docs", "The Odin Project", "freeCodeCamp Node"],
    "Data Science": ["Kaggle Learn", "DataCamp", "IBM Data Science (Coursera)"],
    "Git": ["Pro Git Book", "Learn Git Branching", "GitHub Skills"],
}


# ──────────────────────────── AI Engine ────────────────────────────

class SkillSyncAI:
    """Main orchestrator for all AI sub-systems."""

    # ─── Profile Analyzer ───

    def analyze_profile(self, user):
        """Score profile completeness and detect skill gaps."""
        fields = {
            "name": (bool(user.name and len(user.name) > 1), 10, "Add your full name"),
            "bio": (bool(user.bio and len(user.bio) > 20), 15, "Write a compelling bio (at least 2-3 sentences describing your background)"),
            "skills": (bool(user.skills and len(user.get_skills_list()) >= 3), 20, "Add at least 3 relevant skills to your profile"),
            "goals": (bool(user.goals and len(user.get_goals_list()) >= 2), 15, "Set at least 2 career goals to help the AI guide you"),
            "education_level": (bool(user.education_level), 10, "Add your education level"),
            "college_code": (bool(user.college_code), 5, "Add your college/university code"),
            "availability": (bool(user.availability and len(user.availability) > 3), 10, "Set your availability schedule for mentors and peers"),
            "experience": (bool(user.years_experience and user.years_experience > 0), 10, "Add your years of experience"),
            "job_role": (bool(user.job_role), 5, "Specify your current or desired job role"),
        }

        score = 0
        gaps = []
        tips = []
        completed_fields = []

        for field, (is_filled, weight, tip) in fields.items():
            if is_filled:
                score += weight
                completed_fields.append(field)
            else:
                gaps.append({"field": field, "weight": weight, "tip": tip})
                tips.append(tip)

        # Skill gap analysis against desired role
        skill_gap_analysis = []
        user_skills_lower = {s.lower() for s in user.get_skills_list()}
        desired_role = (user.job_role or "").lower().strip()

        # Try to find the closest matching role
        matched_role = None
        for role_key in ROLE_SKILL_MAP:
            if role_key in desired_role or desired_role in role_key:
                matched_role = role_key
                break

        # If no match found, search goals for role hints
        if not matched_role:
            for goal in user.get_goals_list():
                goal_lower = goal.lower()
                for role_key in ROLE_SKILL_MAP:
                    if role_key in goal_lower or any(w in goal_lower for w in role_key.split()):
                        matched_role = role_key
                        break
                if matched_role:
                    break

        if matched_role:
            required = ROLE_SKILL_MAP[matched_role]
            for skill in required:
                if skill.lower() not in user_skills_lower:
                    res = LEARNING_RESOURCES.get(skill, [])
                    skill_gap_analysis.append({
                        "skill": skill,
                        "priority": "high" if SKILL_TREE.get(skill, {}).get("level", 3) <= 2 else "medium",
                        "resources": res[:2] if res else ["Search for online tutorials"]
                    })

        # Determine grade
        if score >= 90:
            grade = "A+"
            grade_label = "Outstanding"
        elif score >= 75:
            grade = "A"
            grade_label = "Excellent"
        elif score >= 60:
            grade = "B"
            grade_label = "Good"
        elif score >= 40:
            grade = "C"
            grade_label = "Needs Work"
        else:
            grade = "D"
            grade_label = "Incomplete"

        return {
            "score": score,
            "grade": grade,
            "grade_label": grade_label,
            "max_score": 100,
            "completed_fields": completed_fields,
            "gaps": gaps,
            "tips": tips[:5],
            "skill_gap": {
                "target_role": matched_role or "general",
                "missing_skills": skill_gap_analysis[:8]
            },
            "summary": self._profile_summary(score, len(gaps), matched_role)
        }

    def _profile_summary(self, score, gap_count, role):
        if score >= 90:
            return f"🌟 Outstanding! Your profile is top-tier. You're well-positioned for {role or 'your career goals'}. Fine-tune the remaining details to make it perfect."
        elif score >= 75:
            target_desc = role or "the roles you're targeting"
            return f"💪 Great profile! You're almost there. Fix {gap_count} small gap(s) to reach completion. Your profile stands out for {target_desc}."
        elif score >= 60:
            return f"📈 Good foundation! {gap_count} areas need attention. Completing your profile will significantly boost your visibility to mentors and recruiters."
        elif score >= 40:
            return f"⚡ Your profile needs work. {gap_count} critical sections are incomplete. Invest 10 minutes now — a complete profile gets 3x more mentor matches."
        else:
            return f"🚀 Let's build your profile from scratch! {gap_count} fields are missing. Complete these and watch your match quality soar."

    # ─── Job Match Engine ───

    def job_match(self, user, career):
        """Compute match % between user and a career posting."""
        user_skills = {s.lower().strip() for s in user.get_skills_list()}
        user_goals = {g.lower().strip() for g in user.get_goals_list()}

        # Parse job requirements and description
        req_text = (career.requirements or "").lower()
        desc_text = (career.description or "").lower()
        title_text = (career.title or "").lower()

        # Extract skill keywords from job posting
        job_keywords = set()
        for skill in SKILL_TREE:
            if skill.lower() in req_text or skill.lower() in desc_text or skill.lower() in title_text:
                job_keywords.add(skill.lower())

        # Also split requirements by common delimiters
        for delim in [",", ";", "\n", "•", "-", "/"]:
            for part in req_text.split(delim):
                part = part.strip()
                if 1 < len(part) < 40:
                    job_keywords.add(part)

        if not job_keywords:
            # Fallback: find any word overlap
            req_words = set(re.findall(r'\b\w+\b', req_text))
            job_keywords = req_words

        # Calculate match
        matched_skills = user_skills.intersection(job_keywords)
        goal_match = user_goals.intersection(job_keywords)

        # Score: skill match (70%) + goal alignment (30%)
        skill_score = (len(matched_skills) / max(len(job_keywords), 1)) * 70 if job_keywords else 35
        goal_score = min(len(goal_match) * 10, 30)
        raw_score = skill_score + goal_score

        # Boost for experience
        if user.years_experience and user.years_experience > 2:
            raw_score = min(raw_score + 5, 100)

        match_pct = min(round(raw_score), 98)  # Cap at 98 to stay realistic

        # Missing skills
        missing = []
        for kw in job_keywords:
            if kw not in user_skills and kw in {s.lower() for s in SKILL_TREE}:
                missing.append(kw.title())

        # Prep time estimate (weeks)
        if match_pct >= 80:
            prep_weeks = random.choice([1, 2])
            prep_label = "1-2 weeks"
        elif match_pct >= 60:
            prep_weeks = random.choice([3, 4])
            prep_label = "3-4 weeks"
        elif match_pct >= 40:
            prep_weeks = random.choice([6, 8])
            prep_label = "6-8 weeks"
        else:
            prep_weeks = random.choice([10, 12])
            prep_label = "10-12 weeks"

        # Learning resources for missing skills
        resources = []
        for skill in missing[:4]:
            res = LEARNING_RESOURCES.get(skill, [])
            if res:
                resources.append({"skill": skill, "resources": res[:2]})

        # Match verdict
        if match_pct >= 80:
            verdict = "🎯 Strong Match! You're highly qualified for this role."
        elif match_pct >= 60:
            verdict = "✅ Good Match! A few skills to brush up and you'll be ready."
        elif match_pct >= 40:
            verdict = "📈 Moderate Match. Focus on the missing skills and you can get there."
        else:
            verdict = "⚡ Growth Opportunity. This role needs significant skill-building — but it's a great target!"

        return {
            "match_percentage": match_pct,
            "verdict": verdict,
            "matched_skills": [s.title() for s in matched_skills][:10],
            "missing_skills": missing[:8],
            "prep_time": prep_label,
            "prep_weeks": prep_weeks,
            "resources": resources,
            "job_title": career.title,
            "company": career.company,
        }

    # ─── Learning Path Generator ───

    def generate_learning_path(self, user):
        """Build a milestone-based learning roadmap."""
        user_skills = {s.lower().strip() for s in user.get_skills_list()}
        user_goals = [g.strip() for g in user.get_goals_list()]

        # Identify target skills from goals
        target_skills = []
        for goal in user_goals:
            goal_lower = goal.lower()
            # Match against skill tree
            for skill_name, info in SKILL_TREE.items():
                if skill_name.lower() in goal_lower or any(w in goal_lower for w in skill_name.lower().split()):
                    if skill_name.lower() not in user_skills:
                        target_skills.append(skill_name)

            # Match against role map
            for role, skills in ROLE_SKILL_MAP.items():
                if role in goal_lower or any(w in goal_lower for w in role.split()):
                    for skill in skills:
                        if skill.lower() not in user_skills:
                            target_skills.append(skill)

        # De-duplicate while preserving order
        seen = set()
        unique_targets = []
        for s in target_skills:
            if s not in seen:
                seen.add(s)
                unique_targets.append(s)

        if not unique_targets:
            # Fallback: suggest trending skills
            unique_targets = ["Python", "JavaScript", "SQL", "Docker", "REST API"]
            unique_targets = [s for s in unique_targets if s.lower() not in user_skills]

        # Build milestones with prerequisites
        milestones = []
        for i, skill in enumerate(unique_targets[:8]):
            info = SKILL_TREE.get(skill, {"level": 3, "domain": "General", "prereqs": []})
            res = LEARNING_RESOURCES.get(skill, [])

            # Check prerequisites
            prereq_status = []
            for prereq in info.get("prereqs", []):
                prereq_status.append({
                    "skill": prereq,
                    "completed": prereq.lower() in user_skills
                })

            est_days = info["level"] * 7  # Rough estimate

            milestones.append({
                "order": i + 1,
                "skill": skill,
                "domain": info.get("domain", "General"),
                "difficulty": info.get("level", 3),
                "estimated_days": est_days,
                "prerequisites": prereq_status,
                "resources": res[:3] if res else ["Search for online courses and tutorials"],
                "status": "completed" if skill.lower() in user_skills else ("in_progress" if i == 0 else "locked"),
            })

        # Calculate overall completion
        completed = sum(1 for m in milestones if m["status"] == "completed")
        total = len(milestones)
        completion_pct = round((completed / max(total, 1)) * 100)

        # Estimated total time
        total_days = sum(m["estimated_days"] for m in milestones if m["status"] != "completed")

        return {
            "goals": user_goals,
            "milestones": milestones,
            "completion_percentage": completion_pct,
            "total_milestones": total,
            "completed_milestones": completed,
            "estimated_days_remaining": total_days,
            "estimated_weeks_remaining": math.ceil(total_days / 7),
            "summary": f"📚 Your personalized learning path has {total} milestones. {completed} completed, {total - completed} remaining. Estimated {math.ceil(total_days / 7)} weeks to completion."
        }

    # ─── Mock Interview ───

    def start_interview(self, user, interview_type="technical"):
        """Start a mock interview session."""
        bank = INTERVIEW_BANK.get(interview_type, INTERVIEW_BANK["technical"])
        # Select 5 questions
        selected = random.sample(bank, min(5, len(bank)))

        return {
            "interview_type": interview_type,
            "total_questions": len(selected),
            "current_question": 0,
            "questions": [q["q"] for q in selected],
            "keywords": [q["keywords"] for q in selected],
            "topics": [q["topic"] for q in selected],
            "scores": [],
            "feedback": [],
            "started_at": datetime.utcnow().isoformat(),
        }

    def evaluate_answer(self, answer, question_idx, interview_data):
        """Evaluate a single interview answer."""
        if question_idx >= len(interview_data.get("keywords", [])):
            return {"error": "Invalid question index"}

        expected_keywords = interview_data["keywords"][question_idx]
        topic = interview_data["topics"][question_idx]
        answer_lower = answer.lower()

        # Score based on keyword hits
        hits = sum(1 for kw in expected_keywords if kw in answer_lower)
        coverage = hits / max(len(expected_keywords), 1)

        # Length bonus
        word_count = len(answer.split())
        length_bonus = min(word_count / 50, 0.2)  # Up to 20% bonus for detailed answers

        raw_score = min((coverage + length_bonus) * 100, 100)
        score = round(raw_score)

        # Generate feedback
        if score >= 80:
            feedback = f"🌟 Excellent answer on {topic}! You covered the key concepts thoroughly. Your explanation was clear and well-structured."
        elif score >= 60:
            feedback = f"✅ Good answer on {topic}! You hit several important points. Consider also mentioning: {', '.join(kw for kw in expected_keywords[:3] if kw not in answer_lower)}."
        elif score >= 40:
            feedback = f"📈 Decent attempt on {topic}. Try to include more specifics. Key concepts to cover: {', '.join(expected_keywords[:4])}."
        else:
            feedback = f"💡 This needs more depth on {topic}. Key points you should discuss: {', '.join(expected_keywords[:5])}. Practice structuring your answer using the STAR method."

        # Strength/weakness
        strengths = [kw for kw in expected_keywords if kw in answer_lower]
        weaknesses = [kw for kw in expected_keywords if kw not in answer_lower]

        return {
            "score": score,
            "feedback": feedback,
            "topic": topic,
            "strengths": strengths[:3],
            "areas_to_improve": weaknesses[:3],
            "word_count": word_count,
        }

    def finish_interview(self, interview_data):
        """Compile final interview results."""
        scores = interview_data.get("scores", [])
        if not scores:
            return {"error": "No answers recorded"}

        avg_score = round(sum(scores) / len(scores))
        topics = interview_data.get("topics", [])
        feedback_list = interview_data.get("feedback", [])

        # Find weak areas
        weak_topics = []
        for i, s in enumerate(scores):
            if s < 60 and i < len(topics):
                weak_topics.append(topics[i])

        if avg_score >= 80:
            verdict = "🎯 Interview Ready! You demonstrated strong knowledge and communication skills. You'd perform well in real interviews."
        elif avg_score >= 60:
            verdict = "✅ On the Right Track! Solid foundations with some areas to polish. Review the feedback and practice the weak topics."
        elif avg_score >= 40:
            verdict = "📈 Getting There! Focus on deepening your understanding of core concepts. Practice daily for 2-3 weeks."
        else:
            verdict = "💪 Foundation Building Phase. Don't worry — everyone starts here. Study the weak topics and try again in a week!"

        return {
            "overall_score": avg_score,
            "verdict": verdict,
            "total_questions": len(scores),
            "strong_topics": [topics[i] for i in range(len(scores)) if scores[i] >= 70 and i < len(topics)],
            "weak_topics": weak_topics,
            "feedback_summary": feedback_list,
            "recommendation": f"Focus on: {', '.join(weak_topics[:3])}" if weak_topics else "Keep practicing to maintain your edge!"
        }

    # ─── Connection Recommender ───

    def suggest_connections(self, user, all_users, top_n=6):
        """Find best peer/mentor matches with reasoning."""
        user_skills = {s.lower().strip() for s in user.get_skills_list()}
        user_goals = {g.lower().strip() for g in user.get_goals_list()}

        suggestions = []
        for other in all_users:
            if other.id == user.id:
                continue

            other_skills = {s.lower().strip() for s in other.get_skills_list()}
            other_goals = {g.lower().strip() for g in other.get_goals_list()}

            # Jaccard similarity for skills
            skill_union = user_skills.union(other_skills)
            skill_inter = user_skills.intersection(other_skills)
            skill_sim = len(skill_inter) / max(len(skill_union), 1)

            # Goal alignment
            goal_inter = user_goals.intersection(other_goals)
            goal_skill_match = user_goals.intersection(other_skills)  # their skills match our goals
            goal_align = (len(goal_inter) + len(goal_skill_match) * 2) / max(len(user_goals) + len(other_goals), 1)

            # Compute composite score
            if other.is_mentor and not user.is_mentor:
                # Mentor match: prioritize goal coverage
                score = skill_sim * 30 + goal_align * 50 + 20
                conn_type = "mentor"
                reason_parts = []
                if goal_skill_match:
                    reason_parts.append(f"can teach you {', '.join(s.title() for s in list(goal_skill_match)[:3])}")
                if skill_inter:
                    reason_parts.append(f"shares knowledge in {', '.join(s.title() for s in list(skill_inter)[:2])}")
                reason = "; ".join(reason_parts) or "Experienced mentor in your area of interest"
            elif not other.is_mentor and not user.is_mentor:
                # Peer match: prioritize shared goals + complementary skills
                complementary = other_skills - user_skills
                score = skill_sim * 20 + goal_align * 40 + min(len(complementary) * 5, 30) + 10
                conn_type = "study_partner"
                reason_parts = []
                if goal_inter:
                    reason_parts.append(f"shares your goal of {', '.join(g.title() for g in list(goal_inter)[:2])}")
                if complementary:
                    reason_parts.append(f"can help with {', '.join(s.title() for s in list(complementary)[:2])}")
                reason = "; ".join(reason_parts) or "Fellow learner with aligned interests"
            else:
                score = skill_sim * 40 + goal_align * 30 + 15
                conn_type = "peer"
                reason = "Complementary skill set for collaboration"

            suggestions.append({
                "user_id": other.id,
                "name": other.name,
                "role": "Mentor" if other.is_mentor else "Learner",
                "skills": other.get_skills_list()[:5],
                "connection_type": conn_type,
                "match_score": min(round(score), 98),
                "reason": reason,
                "initial": other.name[0] if other.name else "?",
            })

        suggestions.sort(key=lambda x: x["match_score"], reverse=True)
        return suggestions[:top_n]

    # ─── Weekly Insights ───

    def weekly_insights(self, user, db_session):
        """Generate weekly performance summary from DB data."""
        from models import Post, MentorSession, SkillProgress, PeerConnection, PostComment

        week_ago = datetime.utcnow() - timedelta(days=7)

        # Posts created
        posts_count = Post.query.filter(
            Post.user_id == user.id,
            Post.created_at >= week_ago
        ).count()

        # Sessions completed
        sessions_completed = MentorSession.query.filter(
            ((MentorSession.learner_id == user.id) | (MentorSession.mentor_id == user.id)),
            MentorSession.status == 'completed',
            MentorSession.updated_at >= week_ago
        ).count()

        sessions_scheduled = MentorSession.query.filter(
            ((MentorSession.learner_id == user.id) | (MentorSession.mentor_id == user.id)),
            MentorSession.status == 'scheduled'
        ).count()

        # Skills progressed
        skills_updated = SkillProgress.query.filter(
            SkillProgress.user_id == user.id,
            SkillProgress.last_updated >= week_ago
        ).count()

        # All skills for chart
        all_skills = SkillProgress.query.filter_by(user_id=user.id).all()
        skill_data = [{"name": s.skill_name, "level": round(s.level * 100)} for s in all_skills]

        # Connections made
        connections_sent = PeerConnection.query.filter(
            PeerConnection.sender_id == user.id,
            PeerConnection.created_at >= week_ago
        ).count()

        connections_received = PeerConnection.query.filter(
            PeerConnection.receiver_id == user.id,
            PeerConnection.created_at >= week_ago
        ).count()

        # Comments made
        comments_count = PostComment.query.filter(
            PostComment.user_id == user.id,
            PostComment.created_at >= week_ago
        ).count()

        # Engagement score
        engagement = (posts_count * 10 + comments_count * 5 + sessions_completed * 20 +
                      skills_updated * 15 + connections_sent * 8)
        engagement_score = min(engagement, 100)

        # Narrative summary
        highlights = []
        if posts_count > 0:
            highlights.append(f"📝 You shared {posts_count} post{'s' if posts_count > 1 else ''}")
        if sessions_completed > 0:
            highlights.append(f"🎓 Completed {sessions_completed} mentoring session{'s' if sessions_completed > 1 else ''}")
        if skills_updated > 0:
            highlights.append(f"📈 Updated progress on {skills_updated} skill{'s' if skills_updated > 1 else ''}")
        if connections_sent + connections_received > 0:
            highlights.append(f"🤝 Made {connections_sent + connections_received} new connection{'s' if connections_sent + connections_received > 1 else ''}")
        if comments_count > 0:
            highlights.append(f"💬 Left {comments_count} comment{'s' if comments_count > 1 else ''} on community posts")

        if not highlights:
            highlights.append("🌱 This was a quiet week — let's change that!")

        # Trend
        if engagement_score >= 70:
            trend = "🔥 On Fire!"
            trend_msg = "You're crushing it this week! Keep the momentum going."
        elif engagement_score >= 40:
            trend = "📈 Growing"
            trend_msg = "Good activity this week. Push a bit more to reach the next level."
        elif engagement_score > 0:
            trend = "🌱 Starting"
            trend_msg = "Every journey begins with a step. Try completing a session or posting something!"
        else:
            trend = "😴 Dormant"
            trend_msg = "No activity detected this week. Jump back in — your mentors are waiting!"

        return {
            "engagement_score": engagement_score,
            "trend": trend,
            "trend_message": trend_msg,
            "highlights": highlights,
            "metrics": {
                "posts": posts_count,
                "sessions_completed": sessions_completed,
                "sessions_upcoming": sessions_scheduled,
                "skills_updated": skills_updated,
                "connections": connections_sent + connections_received,
                "comments": comments_count,
            },
            "skill_data": skill_data,
            "summary": f"Week in Review: {trend} — Engagement score: {engagement_score}/100"
        }

    # ─── Conversational Chat ───

    def chat(self, user, message, history=None):
        """
        Intent-aware conversational AI.
        Classifies user intent and dispatches to the appropriate sub-system,
        or generates a contextual conversational reply.
        """
        msg_lower = message.lower().strip()

        # Intent classification via keyword matching
        intents = {
            "profile_analysis": ["analyze profile", "analyze my profile", "profile score", "profile strength", "how is my profile", "check my profile",
                                 "profile review", "profile completeness", "improve profile", "profile tips", "review my profile"],
            "skill_gap": ["skill gap", "missing skills", "what skills", "skills i need", "what should i learn"],
            "learning_path": ["learning path", "roadmap", "what to learn", "learning plan", "study plan",
                              "career path", "growth path", "learning roadmap", "upskill", "create a learning", "learning path for me"],
            "mock_interview": ["mock interview", "practice interview", "interview prep", "interview question",
                               "interview me", "practice questions"],
            "weekly_insights": ["weekly", "my progress", "how am i doing", "insights", "my activity", "this week",
                                "performance", "my stats", "weekly insights"],
            "connections": ["find connections", "suggest mentors", "find peers", "who should i connect",
                            "recommend people", "find mentor", "study partner", "connections for me", "find connections for me"],
            "job_advice": ["job", "career advice", "should i apply", "job tips", "resume", "interview tips"],
            "greeting": ["hi", "hello", "hey", "good morning", "good evening", "what's up", "howdy", "sup"],
            "thanks": ["thank", "thanks", "appreciate", "helpful"],
            "help": ["help", "what can you do", "features", "capabilities", "how to use"],
        }

        detected_intent = "general"
        for intent, keywords in intents.items():
            if any(kw in msg_lower for kw in keywords):
                detected_intent = intent
                break

        # Generate response based on intent
        user_name = user.name.split()[0] if user.name else "there"
        confidence = 0.9

        if detected_intent == "greeting":
            responses = [
                f"Hey {user_name}! 👋 I'm your AI Career Mentor. I can analyze your profile, match you to jobs, create learning paths, run mock interviews, and more. What would you like to explore?",
                f"Hello {user_name}! 🌟 Ready to level up your career? I can help with profile optimization, skill gap analysis, interview prep, and personalized learning paths. What's on your mind?",
                f"Hi {user_name}! 🚀 Welcome to your AI career assistant. I'm here to help you grow. Try asking me to analyze your profile or suggest a learning path!",
            ]
            return {"response": random.choice(responses), "intent": detected_intent, "confidence": 95, "action": None}

        elif detected_intent == "help":
            return {
                "response": f"Here's what I can do for you, {user_name}:\n\n"
                    "🔍 **Analyze Profile** — Get your profile strength score and improvement tips\n"
                    "💼 **Job Matching** — See how well you match specific jobs\n"
                    "📚 **Learning Path** — Get a personalized roadmap based on your goals\n"
                    "🎤 **Mock Interview** — Practice technical and behavioral interviews\n"
                    "📊 **Weekly Insights** — See your platform activity and growth metrics\n"
                    "🤝 **Find Connections** — Discover mentors, peers, and study partners\n\n"
                    "Try clicking the quick-action chips below, or just ask me anything!",
                "intent": detected_intent,
                "confidence": 98,
                "action": None,
            }

        elif detected_intent == "thanks":
            responses = [
                f"You're welcome, {user_name}! 😊 I'm always here to help. Is there anything else you'd like to explore?",
                f"Happy to help! 🙌 Feel free to ask me anything else — whether it's career advice, interview prep, or skill planning.",
                f"My pleasure, {user_name}! 💫 Keep pushing forward — you're doing great. Need anything else?",
            ]
            return {"response": random.choice(responses), "intent": detected_intent, "confidence": 95, "action": None}

        elif detected_intent == "profile_analysis":
            return {
                "response": f"Let me analyze your profile, {user_name}... I'll check completeness, identify skill gaps, and give you a personalized improvement roadmap. 🔍",
                "intent": detected_intent,
                "confidence": 95,
                "action": "profile_analysis",
            }

        elif detected_intent == "skill_gap":
            analysis = self.analyze_profile(user)
            skill_gap = analysis["skill_gap"]
            if skill_gap["missing_skills"]:
                missing = ", ".join(s["skill"] for s in skill_gap["missing_skills"][:5])
                response = f"Based on your target role as **{skill_gap['target_role'].title()}**, here are the skills you should focus on:\n\n"
                for s in skill_gap["missing_skills"][:5]:
                    response += f"• **{s['skill']}** ({s['priority']} priority) — Resources: {', '.join(s['resources'][:2])}\n"
                response += f"\nWant me to create a detailed learning path for these skills?"
            else:
                response = f"Great news, {user_name}! Your skills look well-aligned with your goals. Consider adding more specific goals to your profile for deeper analysis."

            return {"response": response, "intent": detected_intent, "confidence": 90, "action": None}

        elif detected_intent == "learning_path":
            return {
                "response": f"I'm generating a personalized learning roadmap based on your goals and current skills, {user_name}. This includes milestone tracking, prerequisites, and curated resources. 📚",
                "intent": detected_intent,
                "confidence": 92,
                "action": "learning_path",
            }

        elif detected_intent == "mock_interview":
            return {
                "response": f"Let's practice! 🎤 I have both **Technical** and **Behavioral** interview questions ready.\n\n"
                    "I'll ask you 5 questions, evaluate your answers, and give detailed feedback with a score.\n\n"
                    "Which type would you prefer?\n"
                    "• **Technical** — Data structures, algorithms, system design\n"
                    "• **Behavioral** — Teamwork, problem-solving, leadership",
                "intent": detected_intent,
                "confidence": 95,
                "action": "mock_interview",
            }

        elif detected_intent == "weekly_insights":
            return {
                "response": f"Let me pull up your weekly activity report, {user_name}. I'll analyze your posts, sessions, skill progress, and connections. 📊",
                "intent": detected_intent,
                "confidence": 93,
                "action": "weekly_insights",
            }

        elif detected_intent == "connections":
            return {
                "response": f"I'll find the best mentors, peers, and study partners for you based on skill similarity, goal alignment, and activity patterns. 🤝",
                "intent": detected_intent,
                "confidence": 91,
                "action": "connection_suggestions",
            }

        elif detected_intent == "job_advice":
            skills_list = ", ".join(user.get_skills_list()[:5]) or "not specified yet"
            goals_list = ", ".join(user.get_goals_list()[:3]) or "not set yet"
            response = (
                f"Here's my career advice based on your profile, {user_name}:\n\n"
                f"**Your Skills:** {skills_list}\n"
                f"**Your Goals:** {goals_list}\n\n"
                "💡 **Tips:**\n"
                "• Keep your profile 100% complete — recruiters filter by completeness\n"
                "• Practice coding challenges daily on LeetCode or HackerRank\n"
                "• Build 2-3 portfolio projects that showcase your target skills\n"
                "• Network with mentors on this platform — they can refer you!\n"
                "• Take mock interviews weekly to build confidence\n\n"
                "Want me to match you with specific jobs in the Careers section?"
            )
            return {"response": response, "intent": detected_intent, "confidence": 88, "action": None}

        else:
            # General conversational response
            responses = [
                f"That's a great question, {user_name}! While I specialize in career coaching, skill analysis, and interview prep, I'm happy to help however I can. Try asking me to analyze your profile, suggest a learning path, or run a mock interview!",
                f"Interesting thought, {user_name}! 🤔 As your AI Career Mentor, I work best with career-related queries. Here are some things you can try:\n• 'Analyze my profile'\n• 'Create a learning path'\n• 'Start a mock interview'\n• 'Show my weekly insights'",
                f"I appreciate you reaching out, {user_name}! Let me focus on what I do best — boosting your career. Try one of the quick-action buttons below to get started!",
            ]
            confidence = 70
            return {"response": random.choice(responses), "intent": detected_intent, "confidence": confidence, "action": None}
