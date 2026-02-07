import re
import pandas as pd
import os
import urllib.parse
from datetime import datetime

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

def save_to_excel(job_title, email_address):
    """
    Saves the job application details to an Excel file.
    
    Args:
        job_title (str): The title of the job.
        email_address (str): The recruiter's email address.
    """
    file_path = "job_application_tracker.xlsx"
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
