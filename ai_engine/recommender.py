from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SkillMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
    
    def find_matches(self, current_user, all_users, top_n=5):
        if len(all_users) == 0:
            return []
        
        user_texts = []
        user_data = []
        
        current_text = self._create_user_text(current_user)
        
        for user in all_users:
            if user.id != current_user.id:
                if current_user.is_mentor and not user.is_mentor:
                    user_texts.append(self._create_user_text(user))
                    user_data.append(user)
                elif not current_user.is_mentor and user.is_mentor:
                    user_texts.append(self._create_user_text(user))
                    user_data.append(user)
        
        if len(user_texts) == 0:
            return []
        
        all_texts = [current_text] + user_texts
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            current_vector = tfidf_matrix[0:1]
            other_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(current_vector, other_vectors)[0]
            
            matches = []
            for idx, similarity in enumerate(similarities):
                matches.append({
                    'user': user_data[idx],
                    'similarity': float(similarity),
                    'percentage': int(similarity * 100)
                })
            
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            return matches[:top_n]
        except Exception as e:
            print(f"Error in matching: {e}")
            return []
    
    def _create_user_text(self, user):
        skills = ' '.join(user.get_skills_list())
        goals = ' '.join(user.get_goals_list())
        return f"{skills} {goals} {user.bio}"
