import os
import json
def get_github_projects(profile_url, job_description=None, top_n=3, cached_data=None):
    """
    Ranks pre-fetched GitHub projects based on the Job Description.
    This function NO LONGER scrapes GitHub at runtime. It relies on the 
    offline-synced `cached_data` passed from app.py.
    """
    try:
        if not cached_data:
            return []
            
        # If no JD, just return top N
        if not job_description:
            return cached_data[:top_n]
            
        def rank_relevance(repo):
            score = 0
            jd = job_description.lower()
            name = (repo.get('name') or "").lower()
            desc = (repo.get('description') or "").lower()
            lang = (repo.get('language') or "").lower()
            summary = (repo.get('summary') or "").lower()
            
            # Simple keyword matching heuristic
            if name and name in jd: score += 5
            if desc and any(word in desc for word in jd.split()): score += 3
            if lang and lang in jd: score += 2
            
            # Match against the LLM-generated summary
            if summary:
                matches = sum(1 for word in jd.split() if len(word) > 4 and word in summary)
                score += min(matches, 10) # cap bonus
                
            return score
            
        ranked = sorted(cached_data, key=rank_relevance, reverse=True)
        return ranked[:top_n]
        
    except Exception as e:
        print(f"Error in get_github_projects: {e}")
        return []
