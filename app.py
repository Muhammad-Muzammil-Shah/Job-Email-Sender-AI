from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
import os
import json
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import timedelta, datetime
from resume_parser import extract_text_from_pdf
from email_agent import generate_job_application_email
from resume_matcher import find_best_resume
from utils import extract_email, save_to_excel, create_gmail_url, get_tracker_path, get_resumes_dir
from outlook_sender import send_smtp_email, send_email_via_local_outlook, LOCAL_OUTLOOK_AVAILABLE
from github_export import get_cached_projects, save_projects_cache, generate_pdf_report, generate_word_report, get_github_data_dir

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'job-email-sender-secret-key-2024')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# ─── Session Management ─────────────────────────────────────────────

@app.before_request
def ensure_user_id():
    session.permanent = True
    ls_user_id = request.args.get('sync_user_id')
    if ls_user_id and len(ls_user_id) == 36:
        session['user_id'] = ls_user_id
    elif 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

@app.route('/api/get_user_id')
def get_user_id():
    return jsonify({'user_id': session.get('user_id', '')})

@app.route('/api/set_user_id', methods=['POST'])
def set_user_id():
    data = request.get_json() or {}
    ls_user_id = data.get('user_id', '')
    if ls_user_id and len(ls_user_id) == 36:
        session['user_id'] = ls_user_id
        return jsonify({'success': True, 'user_id': ls_user_id})
    return jsonify({'success': False, 'user_id': session.get('user_id', '')})


# ─── Helper: Get Application Stats ──────────────────────────────────

def _get_app_stats(user_id):
    """Returns dict with total_applications, today_applications, this_week counts."""
    import pandas as pd
    path = get_tracker_path(user_id)
    stats = {'total_applications': 0, 'today_applications': 0, 'this_week': 0}
    if os.path.exists(path):
        try:
            df = pd.read_excel(path)
            if not df.empty:
                stats['total_applications'] = len(df)
                today = datetime.now().date()
                week_ago = today - timedelta(days=7)
                for _, row in df.iterrows():
                    try:
                        date_str = str(row.get('Date Applied', ''))
                        if date_str:
                            applied_date = pd.to_datetime(date_str).date()
                            if applied_date == today:
                                stats['today_applications'] += 1
                            if applied_date >= week_ago:
                                stats['this_week'] += 1
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error reading tracker: {e}")
    return stats


# ─── Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Home page: JD input + stats."""
    user_id = session.get('user_id')
    user_resumes_dir = get_resumes_dir(user_id)
    local_resumes = [f for f in os.listdir(user_resumes_dir) if f.lower().endswith('.pdf')]
    stats = _get_app_stats(user_id)
    return render_template('index.html',
                           resume_count=len(local_resumes),
                           has_resume=len(local_resumes) > 0,
                           **stats)


@app.route('/generate', methods=['POST'])
def generate():
    """Process JD, match resumes, scrape GitHub, generate email → preview."""
    user_id = session.get('user_id')
    user_resumes_dir = get_resumes_dir(user_id)
    job_description = request.form.get('job_description')

    if not job_description:
        flash('Please enter a Job Description.')
        return redirect(url_for('index'))

    # --- Resume Processing with Caching ---
    user_resumes_dir = get_resumes_dir(user_id)
    local_resumes = [f for f in os.listdir(user_resumes_dir) if f.lower().endswith('.pdf')]
    
    if not local_resumes:
        flash('No resumes found. Please upload one in your Profile.')
        return redirect(url_for('profile'))

    # Load cache
    cache_path = os.path.join(get_github_data_dir(user_id), "resume_cache.json")
    resume_cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                resume_cache = json.load(f)
        except Exception:
            pass

    resume_texts = {}
    cache_updated = False

    for name in local_resumes:
        path = os.path.join(user_resumes_dir, name)
        mtime = os.path.getmtime(path)
        
        # Check cache
        if name in resume_cache and resume_cache[name].get('mtime') == mtime:
            resume_texts[name] = resume_cache[name].get('text')
        else:
            # Re-extract
            try:
                with open(path, "rb") as f:
                    text = extract_text_from_pdf(f.read())
                    if text:
                        resume_texts[name] = text
                        resume_cache[name] = {'text': text, 'mtime': mtime}
                        cache_updated = True
            except Exception as e:
                print(f"Error reading {name}: {e}")

    # Save cache if updated
    if cache_updated:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(resume_cache, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving resume cache: {e}")

    if not resume_texts:
        flash("Could not extract text from any resume.")
        return redirect(url_for('profile'))

    # Best resume matching
    final_resume_name = next(iter(resume_texts))
    final_resume_text = resume_texts[final_resume_name]
    if len(resume_texts) > 1:
        match_result = find_best_resume(job_description, resume_texts)
        best = match_result.get("best_resume_filename")
        if best and best in resume_texts:
            final_resume_name = best
            final_resume_text = resume_texts[best]

    # GitHub projects: strictly use cached/summarized data
    github_profile = session.get('github_profile')
    github_projects = []
    github_error = None
    all_github_projects = []  # full list for context
    if github_profile:
        # Only use pre-synced cached data
        cached, cached_at, cached_url = get_cached_projects(user_id)
        if cached and cached_url == github_profile:
            all_github_projects = cached
            # Rank top 3 relevant for this JD based on summaries
            from github_project_agent import get_github_projects
            try:
                # We pass 'cached' directly so it doesn't scrape
                github_projects = get_github_projects(github_profile, job_description, top_n=3, cached_data=cached)
            except Exception as e:
                github_error = str(e)
        else:
            github_error = "GitHub projects not synced. Please go to your Profile and click 'Sync Projects'."

    # Generate email
    recruiter_email = extract_email(job_description)
    email_content = generate_job_application_email(job_description, final_resume_text, github_projects=github_projects)

    # Store in session (keep projects minimal to avoid cookie overflow)
    session_projects = [
        {"name": p.get("name", ""), "url": p.get("url", ""), "description": p.get("description", "")}
        for p in (github_projects or [])
    ]
    session['email_data'] = {
        "recruiter_email": recruiter_email or "",
        "subject": email_content.get("subject", ""),
        "body": email_content.get("body", ""),
        "resume_name": final_resume_name,
        "job_title": email_content.get("job_title", "Job Application"),
        "github_projects": session_projects,
        "github_error": github_error
    }

    # Pass full projects (with summaries) to template directly, not via session
    display_data = dict(session['email_data'])
    display_data['github_projects'] = github_projects or []
    return render_template('generate.html', data=display_data, local_outlook=LOCAL_OUTLOOK_AVAILABLE)


@app.route('/send', methods=['POST'])
def send():
    """Send the email or save to tracker."""
    data = session.get('email_data')
    if not data:
        return redirect(url_for('index'))

    user_id = session.get('user_id')
    user_resumes_dir = get_resumes_dir(user_id)

    recipient = request.form.get('recipient')
    subject = request.form.get('subject')
    body = request.form.get('body')
    service = request.form.get('service')
    email_user = request.form.get('email_user')
    email_pass = request.form.get('email_pass')
    method = request.form.get('send_method')

    # Update session
    data['recruiter_email'] = recipient
    data['subject'] = subject
    data['body'] = body
    session['email_data'] = data

    resume_path = os.path.join(user_resumes_dir, data['resume_name'])

    if method == 'desktop' and LOCAL_OUTLOOK_AVAILABLE:
        success, msg = send_email_via_local_outlook(recipient, subject, body, resume_path)
        if success:
            save_to_excel(data.get('job_title', 'Job Application'), recipient, user_id=user_id)
            flash(f"✅ Sent via Outlook Desktop! {msg}")
            return redirect(url_for('index'))
        else:
            flash(f"❌ Error sending via Outlook: {msg}")

    elif method == 'smtp':
        if not email_user or not email_pass:
            flash("❌ Credentials missing for SMTP sending.")
        else:
            with open(resume_path, "rb") as f:
                resume_bytes = f.read()

            safe_service = service if service else "outlook"
            success, msg = send_smtp_email(
                recipient, subject, body,
                resume_bytes, data['resume_name'],
                email_user, email_pass, safe_service
            )
            if success:
                save_to_excel(data.get('job_title', 'Job Application'), recipient, user_id=user_id)
                flash(f"✅ Sent successfully via {safe_service.title()}!")
                return redirect(url_for('index'))
            else:
                flash(f"❌ Failed to send via {safe_service.title()}: {msg}")

    # On failure or unexpected method, re-render generate page
    return render_template('generate.html', data=data, local_outlook=LOCAL_OUTLOOK_AVAILABLE)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    """Profile management: resumes, GitHub, credentials."""
    user_id = session.get('user_id')
    user_resumes_dir = get_resumes_dir(user_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'upload_resume':
            if 'resume_files' not in request.files:
                flash('No file selected.')
                return redirect(request.url)
            files = request.files.getlist('resume_files')
            count = 0
            for file in files:
                if file and file.filename and file.filename.lower().endswith('.pdf'):
                    filename = secure_filename(file.filename)
                    if filename:
                        file.save(os.path.join(user_resumes_dir, filename))
                        count += 1
            flash(f'✅ {count} resume{"s" if count != 1 else ""} uploaded successfully.')
            return redirect(request.url)

        elif action == 'github_save':
            github_profile = request.form.get('github_profile')
            github_token = request.form.get('github_token')
            session['github_profile'] = github_profile
            session['github_token'] = github_token
            flash('✅ GitHub settings saved.')
            return redirect(request.url)

    local_resumes = [f for f in os.listdir(user_resumes_dir) if f.lower().endswith('.pdf')]
    # Load cached GitHub data
    cached_projects, cached_at, cached_url = get_cached_projects(user_id)
    return render_template('profile.html',
                           resumes=local_resumes,
                           github_profile=session.get('github_profile', ''),
                           github_token=session.get('github_token', ''),
                           cached_projects=cached_projects or [],
                           cached_at=cached_at or '',
                           cached_project_count=len(cached_projects) if cached_projects else 0)


@app.route('/delete_resume/<filename>')
def delete_resume(filename):
    try:
        user_id = session.get('user_id')
        path = os.path.join(get_resumes_dir(user_id), secure_filename(filename))
        if os.path.exists(path):
            os.remove(path)
            flash(f"🗑️ Deleted {filename}")
    except Exception as e:
        flash(f"❌ Error deleting: {e}")
    return redirect(url_for('profile'))


@app.route('/sync_github')
def sync_github():
    """Force re-scrape GitHub projects, summarize them, and cache them."""
    user_id = session.get('user_id')
    github_profile = session.get('github_profile')
    github_token = session.get('github_token')

    if not github_profile:
        flash('❌ No GitHub profile set. Go to Profile to add one.')
        return redirect(url_for('profile'))

    try:
        from github_scraper import extract_username, fetch_repos, filter_repo_details, fetch_readme, summarize_readme
        if github_token:
            os.environ['GITHUB_TOKEN'] = github_token
        username = extract_username(github_profile)
        repos = fetch_repos(username)
        filtered = filter_repo_details(repos)
        for repo in filtered:
            readme = fetch_readme(username, repo.get('name'))
            # Generate a 100-150 word summary instead of storing the full raw text
            summary = summarize_readme(repo.get('name'), readme, repo.get('description'), repo.get('language'))
            repo['summary'] = summary
        
        save_projects_cache(user_id, filtered, github_profile)
        # Generate PDF and Word reports using the summaries
        generate_pdf_report(user_id, filtered, github_profile)
        generate_word_report(user_id, filtered, github_profile)
        flash(f'✅ Synced & Summarized {len(filtered)} projects! Reports updated.')
    except Exception as e:
        flash(f'❌ Sync failed: {e}')

    return redirect(url_for('profile'))


@app.route('/download_github_pdf')
def download_github_pdf():
    user_id = session.get('user_id')
    cached, _, cached_url = get_cached_projects(user_id)
    if not cached:
        flash('❌ No cached GitHub data. Scrape first.')
        return redirect(url_for('profile'))
    path = generate_pdf_report(user_id, cached, cached_url or '')
    return send_file(path, as_attachment=True, download_name='GitHub_Projects_Portfolio.pdf')


@app.route('/download_github_word')
def download_github_word():
    user_id = session.get('user_id')
    cached, _, cached_url = get_cached_projects(user_id)
    if not cached:
        flash('❌ No cached GitHub data. Scrape first.')
        return redirect(url_for('profile'))
    path = generate_word_report(user_id, cached, cached_url or '')
    return send_file(path, as_attachment=True, download_name='GitHub_Projects_Portfolio.docx')


@app.route('/tracker')
def tracker():
    """Application history with stats and data table."""
    import pandas as pd
    user_id = session.get('user_id')
    path = get_tracker_path(user_id)

    data = []
    has_data = False
    stats = _get_app_stats(user_id)

    if os.path.exists(path):
        try:
            df = pd.read_excel(path)
            if not df.empty:
                has_data = True
                data = df.to_dict('records')
        except Exception as e:
            print(f"Error reading tracker: {e}")

    return render_template('tracker.html',
                           data=data,
                           has_data=has_data,
                           **stats)


@app.route('/download_tracker')
def download_tracker():
    user_id = session.get('user_id')
    path = get_tracker_path(user_id)
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name="job_application_tracker.xlsx")
    flash("No tracker file found.")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
