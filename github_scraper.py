import requests
import json
import re
import os

def extract_username(profile_url):
    match = re.search(r"github.com/([A-Za-z0-9-]+)", profile_url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid GitHub profile URL.")

def fetch_repos(username):
    repos = []
    page = 1
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < 100:
                break
            page += 1
        else:
            raise Exception(f"Failed to fetch repos: {response.status_code} - {response.text}")
    return repos

def filter_repo_details(repos):
    filtered = []
    for repo in repos:
        filtered.append({
            'name': repo.get('name'),
            'url': repo.get('html_url'),
            'description': repo.get('description'),
            'language': repo.get('language'),
        })
    return filtered

def save_to_file(data, filename="github_projects.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_readme(owner, repo_name):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        return None

def summarize_readme(repo_name, readme_text, description, language):
    """Summarizes a repo's README using Groq. Returns a short description if no README."""
    if not readme_text or readme_text == "README not found.":
        # Fallback if no README
        desc = description if description else "No description provided."
        lang_str = f" Built with {language}." if language else ""
        return f"{repo_name}: {desc}{lang_str}"
        
    try:
        from groq import Groq
        from dotenv import load_dotenv
        load_dotenv()
        
        client = Groq()
        prompt = f"""
        Summarize the following GitHub repository README into a highly concise, professional 100-150 word summary.
        Focus strictly on: 
        1. The core problem it solves. 
        2. The primary tech stack used.
        3. The main features or impact.
        Do NOT use any markdown formatting (no stars, bolding, or lists). Write it as a fluid paragraph.
        Repository Name: {repo_name}
        
        README Content:
        {readme_text[:5000]} # truncate to avoid token limits
        """
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a senior technical writer summarizing code repositories."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=250,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error summarizing {repo_name}: {e}")
        # Fallback on error
        desc = description if description else "No description provided."
        lang_str = f" Built with {language}." if language else ""
        return f"{repo_name}: {desc}{lang_str} (Summarization failed)"

def main():
    profile_url = input("Enter GitHub profile URL: ")
    # Optionally prompt for token if not set
    if not os.environ.get("GITHUB_TOKEN"):
        token = input("Enter your GitHub Personal Access Token (or press Enter to skip): ")
        if token:
            os.environ["GITHUB_TOKEN"] = token
    try:
        username = extract_username(profile_url)
        repos = fetch_repos(username)
        filtered = filter_repo_details(repos)
        # Fetch README for each repo and summarize it
        print("Fetching and summarizing projects. This may take a moment...")
        for repo in filtered:
            repo_name = repo.get('name')
            readme = fetch_readme(username, repo_name)
            summary = summarize_readme(repo_name, readme, repo.get('description'), repo.get('language'))
            repo['summary'] = summary
            print(f"Summarized: {repo_name}")
            
        save_to_file(filtered)
        print(f"Saved {len(filtered)} projects (name, url, summary) to github_projects.json")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
