import re
import pandas as pd
import os
import urllib.parse
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def get_tracker_path():
    """
    Returns the persistent path for the Excel tracker file.
    On Azure (Linux), it uses /home/data to persist across deployments.
    On Local (Windows/Mac), it uses the current directory.
    """
    # Check if running on Azure (Linux environment generally)
    if os.name == 'posix' and os.getenv('WEBSITE_SITE_NAME'):
        # Azure App Service specific persistence path
        data_dir = "/home/data"
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir)
            except OSError:
                # Fallback if permission denied
                return "job_application_tracker.xlsx"
        return os.path.join(data_dir, "job_application_tracker.xlsx")
    
    # Local development
    return "job_application_tracker.xlsx"

def get_resumes_dir():
    """
    Returns the persistent directory for storing resumes.
    """
    if os.name == 'posix' and os.getenv('WEBSITE_SITE_NAME'):
        # Azure persistent storage
        resume_path = "/home/data/resumes"
    else:
        # Local storage
        resume_path = "resumes"
        
    if not os.path.exists(resume_path):
        try:
            os.makedirs(resume_path)
        except OSError:
            pass # Handle permission issues if any
            
    return resume_path

def create_gmail_url(to_email, subject, body):
    """
    Creates a direct URL to compose a Gmail message.
    """
    base_url = "https://mail.google.com/mail/?view=cm&fs=1"
    params = {
        "to": to_email,
        "su": subject,
        "body": body
    }
    return f"{base_url}&{urllib.parse.urlencode(params)}"

def extract_email(text: str) -> str:
    """
    Extracts the first email address found in the text using regex.
    
    Args:
        text (str): The text to search.
        
    Returns:
        str: The extracted email or None if not found.
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    if match:
        return match.group(0)
    return None

def save_to_google_sheet(job_title, email_address):
    """
    Saves data to Google Sheets if configured.
    """
    try:
        # Check for credentials in environment variable
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Job Application Tracker")
        
        if not creds_json:
            return False, "GOOGLE_CREDENTIALS_JSON not found in environment."

        # Define scope
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Authenticate with credentials from JSON string
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Open the sheet
        try:
            sheet = client.open(sheet_name).sheet1
        except gspread.SpreadsheetNotFound:
            return False, f"Spreadsheet '{sheet_name}' not found. Please share it with the service account email."

        # Append row
        date_applied = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [job_title, email_address, date_applied, "Sent"]
        sheet.append_row(row)
        
        return True, "Saved to Google Sheet successfully."
        
    except Exception as e:
        return False, f"Google Sheet Error: {str(e)}"

def save_to_excel(job_title, email_address):
    """
    Saves the job application details to an Excel file AND Google Sheets.
    
    Args:
        job_title (str): The title of the job.
        email_address (str): The recruiter's email address.
    """
    # 1. Save to Google Sheets (Cloud Persistence)
    gs_success, gs_msg = save_to_google_sheet(job_title, email_address)
    print(f"Google Sheets Status: {gs_msg}")

    # 2. Save to Local/Persistent Excel (Backup)
    file_path = get_tracker_path()
    date_applied = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_data = {
        "Job Title": [job_title],
        "Email Address": [email_address],
        "Date Applied": [date_applied],
        "Status": ["Sent"]
    }
    
    df_new = pd.DataFrame(new_data)
    
    try:
        if os.path.exists(file_path):
            df_existing = pd.read_excel(file_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_excel(file_path, index=False)
        else:
            df_new.to_excel(file_path, index=False)
        return True
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        return False
