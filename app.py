from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import os
import json
import uuid
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import tempfile
from datetime import timedelta
from resume_parser import extract_text_from_pdf
from email_agent import generate_job_application_email
from resume_matcher import find_best_resume
from utils import extract_email, save_to_excel, create_gmail_url, get_tracker_path, get_resumes_dir
from outlook_sender import send_smtp_email, send_email_via_local_outlook, LOCAL_OUTLOOK_AVAILABLE

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'job-email-sender-secret-key-2024')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)  # Session lasts 1 year
# app.config['UPLOAD_FOLDER'] is now dynamic per user, so we handle it in routes
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max limit

@app.before_request
def ensure_user_id():
    session.permanent = True  # Make session persistent
    # Check if user_id is passed via query param (from localStorage sync)
    ls_user_id = request.args.get('sync_user_id')
    if ls_user_id and len(ls_user_id) == 36:  # Valid UUID length
        session['user_id'] = ls_user_id
    elif 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

@app.route('/api/get_user_id')
def get_user_id():
    """API endpoint to get current user_id for localStorage sync."""
    from flask import jsonify
    return jsonify({'user_id': session.get('user_id', '')})

@app.route('/api/set_user_id', methods=['POST'])
def set_user_id():
    """API endpoint to set user_id from localStorage."""
    from flask import jsonify
    data = request.get_json() or {}
    ls_user_id = data.get('user_id', '')
    if ls_user_id and len(ls_user_id) == 36:
        session['user_id'] = ls_user_id
        return jsonify({'success': True, 'user_id': ls_user_id})
    return jsonify({'success': False, 'user_id': session.get('user_id', '')})

@app.route('/')
def index():
    # Page 1: Setup Credentials
    return render_template('setup.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    # Page 2: Upload & Process
    user_id = session.get('user_id')
    user_resumes_dir = get_resumes_dir(user_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'upload_resume':
            if 'resume_files' not in request.files:
                flash('No file part')
                return redirect(request.url)
            files = request.files.getlist('resume_files')
            for file in files:
                if file and file.filename and file.filename.lower().endswith('.pdf'):
                    filename = secure_filename(file.filename)
                    if filename:
                        file.save(os.path.join(user_resumes_dir, filename))
            flash(f'{len(files)} resumes uploaded successfully.')
            return redirect(request.url)
            
        elif action == 'generate':
            job_description = request.form.get('job_description')
            if not job_description:
                flash('Please enter a Job Description.')
                return redirect(request.url)
                
            # Get selected resume logic
            local_resumes = [f for f in os.listdir(user_resumes_dir) if f.lower().endswith('.pdf')]
            
            if not local_resumes:
                flash('No resumes found. Please upload one.')
                return redirect(request.url)
                
            # Process Resumes
            resume_texts = {}
            for name in local_resumes:
                path = os.path.join(user_resumes_dir, name)
                try:
                    with open(path, "rb") as f:
                        text = extract_text_from_pdf(f.read())
                        if text: resume_texts[name] = text
                except Exception as e:
                    print(f"Error reading {name}: {e}")

            if not resume_texts:
                flash("Could not extract text from any resume.")
                return redirect(request.url)

            # Match Logic
            final_resume_name = next(iter(resume_texts))
            final_resume_text = resume_texts[final_resume_name]
            
            if len(resume_texts) > 1:
                match_result = find_best_resume(job_description, resume_texts)
                best = match_result.get("best_resume_filename")
                if best and best in resume_texts:
                    final_resume_name = best
                    final_resume_text = resume_texts[best]
            
            # Generate Email
            recruiter_email = extract_email(job_description)
            email_content = generate_job_application_email(job_description, final_resume_text)
            
            # Store in Session
            session['email_data'] = {
                "recruiter_email": recruiter_email or "",
                "subject": email_content.get("subject", ""),
                "body": email_content.get("body", ""),
                "resume_name": final_resume_name,
                "job_title": email_content.get("job_title", "Job Application")
            }
            
            return redirect(url_for('preview'))

    # GET Request: Show Upload Page
    local_resumes = [f for f in os.listdir(user_resumes_dir) if f.lower().endswith('.pdf')]
    return render_template('upload.html', resumes=local_resumes)

@app.route('/preview', methods=['GET', 'POST'])
def preview():
    data = session.get('email_data')
    if not data:
        return redirect(url_for('index'))
    
    user_id = session.get('user_id')
    user_resumes_dir = get_resumes_dir(user_id)
    
    if request.method == 'POST':
        # Send Email Logic
        recipient = request.form.get('recipient')
        subject = request.form.get('subject')
        body = request.form.get('body')
        
        # Credentials from Form (Client Side)
        service = request.form.get('service') # 'gmail' or 'outlook'
        email_user = request.form.get('email_user')
        email_pass = request.form.get('email_pass')
        method = request.form.get('send_method') # 'smtp' or 'desktop' or 'browser'

        # Update session with edited data (optional)
        data['recruiter_email'] = recipient
        data['subject'] = subject
        data['body'] = body
        session['email_data'] = data

        resume_path = os.path.join(user_resumes_dir, data['resume_name'])
        
        if method == 'browser':
             # The button is a link in the frontend, handled there or redirect
             pass # Handled by frontend link usually, but if submitted here:
             return redirect(create_gmail_url(recipient, subject, body))

        elif method == 'desktop' and LOCAL_OUTLOOK_AVAILABLE:
            success, msg = send_email_via_local_outlook(recipient, subject, body, resume_path)
            if success:
                flash(f"Sent via Outlook Desktop! {msg}")
                save_to_excel(data['job_title'], recipient, user_id=user_id)
                return redirect(url_for('index'))
            else:
                flash(f"Error: {msg}")

        elif method == 'save_tracker':
            save_to_excel(data['job_title'], recipient, user_id=user_id)
            flash("Saved to Excel tracker successfully!")
            return redirect(url_for('index'))
                
        elif method == 'smtp':
            if not email_user or not email_pass:
                flash("Credentials missing for SMTP sending.")
            else:
                # Read bytes
                with open(resume_path, "rb") as f:
                    resume_bytes = f.read()
                
                # Ensure service is string (default to outlook)
                safe_service = service if service else "outlook"
                
                success, msg = send_smtp_email(
                    recipient, subject, body, 
                    resume_bytes, data['resume_name'], 
                    email_user, email_pass, safe_service
                )
                
                if success:
                    flash(f"Sent successfully via {safe_service.title()}!")
                    save_to_excel(data['job_title'], recipient, user_id=user_id)
                    return redirect(url_for('index'))
                else:
                    flash(f"Failed: {msg}")

    return render_template('preview.html', data=data, local_outlook=LOCAL_OUTLOOK_AVAILABLE)

@app.route('/delete_resume/<filename>')
def delete_resume(filename):
    try:
        user_id = session.get('user_id')
        path = os.path.join(get_resumes_dir(user_id), secure_filename(filename))
        if os.path.exists(path):
            os.remove(path)
            flash(f"Deleted {filename}")
    except Exception as e:
        flash(f"Error deleting: {e}")
    return redirect(url_for('index'))

@app.route('/tracker')
def tracker():
    """View all sent applications in a data table."""
    import pandas as pd
    from datetime import datetime, timedelta
    
    user_id = session.get('user_id')
    path = get_tracker_path(user_id)
    
    data = []
    total_applications = 0
    today_applications = 0
    this_week = 0
    has_data = False
    
    if os.path.exists(path):
        try:
            df = pd.read_excel(path)
            if not df.empty:
                has_data = True
                data = df.to_dict('records')
                total_applications = len(data)
                
                # Calculate stats
                today = datetime.now().date()
                week_ago = today - timedelta(days=7)
                
                for row in data:
                    try:
                        date_str = str(row.get('Date Applied', ''))
                        if date_str:
                            applied_date = pd.to_datetime(date_str).date()
                            if applied_date == today:
                                today_applications += 1
                            if applied_date >= week_ago:
                                this_week += 1
                    except:
                        pass
        except Exception as e:
            print(f"Error reading tracker: {e}")
    
    return render_template('tracker.html', 
                           data=data, 
                           has_data=has_data,
                           total_applications=total_applications,
                           today_applications=today_applications,
                           this_week=this_week)

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
