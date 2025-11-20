class SkillMatcher:
    def __init__(self):
        pass
    
    def find_matches(self, user, all_users, top_n=5):
        """Find matching mentors or learners based on skills and goals"""
        matches_with_scores = []
        
        for other_user in all_users:
            if other_user.id == user.id:
                continue
                
            # Mentors look for learners, learners look for mentors
            if user.is_mentor == other_user.is_mentor:
                continue
                
            # Calculate match score
            score = self.calculate_match_score(user, other_user)
            matches_with_scores.append((other_user, score))
        
        # Sort by match score descending and take top N
        matches_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        return matches_with_scores[:top_n]
    
    def calculate_match_score(self, user1, user2):
        """Calculate match score between two users based on skills and goals"""
        score = 0
        
        # Convert skills and goals to sets for comparison
        user1_skills = set(skill.strip().lower() for skill in user1.skills.split(','))
        user2_skills = set(skill.strip().lower() for skill in user2.skills.split(','))
        user1_goals = set(goal.strip().lower() for goal in user1.goals.split(','))
        user2_goals = set(goal.strip().lower() for goal in user2.goals.split(','))
        
        # Skill overlap
        common_skills = user1_skills.intersection(user2_skills)
        score += len(common_skills) * 10
        
        # Goal alignment
        if user1.is_mentor:
            # Mentor's skills matching learner's goals
            mentor_skills_for_learner_goals = user1_skills.intersection(user2_goals)
            score += len(mentor_skills_for_learner_goals) * 15
        else:
            # Learner's goals matching mentor's skills
            learner_goals_met_by_mentor = user1_goals.intersection(user2_skills)
            score += len(learner_goals_met_by_mentor) * 15
        
        # Ensure score doesn't exceed 100
        return min(score, 100)