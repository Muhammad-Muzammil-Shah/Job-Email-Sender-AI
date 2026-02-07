import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

# Try importing pywin32 modules, handle failure gracefully
try:
    import pythoncom
    import win32com.client as win32
    LOCAL_OUTLOOK_AVAILABLE = True
except ImportError:
    pythoncom = None
    win32 = None
    LOCAL_OUTLOOK_AVAILABLE = False


def send_email_via_local_outlook(to_email, subject, body, attachment_path=None):
    """
    Sends an email using the local Outlook Desktop application.
    """
    if pythoncom is None or win32 is None:
        return False, "Required library 'pywin32' not found. Please run: pip install pywin32"

    try:
        # Initialize COM library for Streamlit thread compatibility
        pythoncom.CoInitialize()
        
        try:
            # Try to grab the running instance first (fixes some permission issues)
            outlook = win32.GetActiveObject('Outlook.Application')
        except Exception:
            # If not running, try to start it
            outlook = win32.Dispatch('Outlook.Application')
            
        mail = outlook.CreateItem(0)
        
        # If specific sender account is needed (optional, otherwise uses default)
        # You can't easily force "From" in local Outlook unless you have "Send As" permissions
        # or iterate through .Session.Accounts to find the right one.
        # identifying account by email:
        target_account = "MuhammadMuzmil.Shah@studentambassadors.com"
        account_found = None
        
        for account in outlook.Session.Accounts:
             if account.SmtpAddress.lower() == target_account.lower():
                 account_found = account
                 break
        
        if account_found:
            mail._oleobj_.Invoke(*(64209, 0, 8, 0, account_found)) # MAPI property for SendUsingAccount
        
        mail.To = to_email
        mail.Subject = subject
        mail.Body = body
        
        if attachment_path:
             mail.Attachments.Add(os.path.abspath(attachment_path))
        
        mail.Send()
        return True, "Email sent successfully via Outlook Desktop!"
        
    except Exception as e:
        error_msg = str(e)
        if "-2146959355" in error_msg or "Server execution failed" in error_msg:
             return False, "Outlook is running with different permissions than this script.\n1. Close Outlook.\n2. Re-open Outlook normally (NOT as Admin).\n3. If VS Code is running as Admin, restart it normally."
        return False, f"Local Outlook Error: {e}. Make sure Outlook is open."

def send_email_via_outlook(to_email, subject, body, attachment_bytes, attachment_name):
    """
    Sends an email using Outlook SMTP server.
    
    Args:
        to_email (str): Recipient email.
        subject (str): Email subject.
        body (str): Email body.
        attachment_bytes (bytes): The file content in bytes.
        attachment_name (str): The filename for the attachment.
        
    Returns:
        tuple: (bool, str) - (Success status, Message)
    """
    smtp_server = "smtp.office365.com"
    smtp_port = 587
    sender_email = os.getenv("OUTLOOK_EMAIL")
    sender_password = os.getenv("OUTLOOK_PASSWORD")

    if not sender_email or not sender_password:
        return False, "Error: Outlook credentials not found in .env"

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        if attachment_bytes and attachment_name:
            part = MIMEApplication(attachment_bytes, Name=attachment_name)
            part['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
            msg.attach(part)

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False, f"SMTP Error: {str(e)}"
