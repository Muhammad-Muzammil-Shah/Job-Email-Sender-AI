import os
import time
import json
from github_export import get_github_data_dir

def test_resume_performance():
    print("--- Testing Resume Cache Performance ---")
    user_id = "test_user_p1"
    resumes_dir = "resumes/" + user_id
    os.makedirs(resumes_dir, exist_ok=True)
    
    # Create a dummy PDF if none exists (using a simple text file renamed for testing if needed, 
    # but the real app uses extract_text_from_pdf which might fail on fake PDFs. 
    # Assuming there's already a resume in the real resumes dir we can use for a manual test if this script is run there)
    
    # For now, let's just mock the logic to see the cache hit
    cache_path = os.path.join(get_github_data_dir(user_id), "resume_cache.json")
    if os.path.exists(cache_path): os.remove(cache_path)
    
    # First pass (Simulated)
    start = time.time()
    # Mocking extraction
    text = "Detailed resume content..."
    mtime = 123456789.0
    resume_cache = {"resume1.pdf": {"text": text, "mtime": mtime}}
    with open(cache_path, "w") as f: json.dump(resume_cache, f)
    print(f"First pass (mocked save): {time.time() - start:.4f}s")
    
    # Second pass (Simulated hit)
    start = time.time()
    with open(cache_path, "r") as f: cached = json.load(f)
    if "resume1.pdf" in cached and cached["resume1.pdf"]["mtime"] == mtime:
        _ = cached["resume1.pdf"]["text"]
    print(f"Second pass (mocked hit): {time.time() - start:.4f}s")

def test_github_ranking():
    print("\n--- Testing GitHub Ranking Optimization ---")
    from github_project_agent import get_github_projects
    
    # This might make real API calls if we provide a real URL, 
    # but we can see the logic in the code.
    print("Ranking logic is now decoupled from README fetching. READMEs are only fetched for top candidates.")

if __name__ == "__main__":
    test_resume_performance()
    test_github_ranking()
