
import streamlit as st
import os
from dotenv import load_dotenv
from resume_parser import extract_text_from_pdf
from email_agent import generate_job_application_email
from resume_matcher import find_best_resume
from utils import extract_email, save_to_excel, create_gmail_url
from outlook_sender import send_email_via_local_outlook, send_email_via_outlook, LOCAL_OUTLOOK_AVAILABLE
import tempfile


# Load environment variables
load_dotenv()

st.set_page_config(page_title="Job Application Assistant", layout="centered")

def init_session_state():
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "email_method" not in st.session_state:
        st.session_state.email_method = "Gmail (Browser)"
    if "email_data" not in st.session_state:
        st.session_state.email_data = None

def main():
    init_session_state()
    st.title("🤖 AI Job Application Assistant")

    # Step 1: Connection / Setup (if not connected)
    if st.session_state.step == 1:
        st.markdown("### Step 1: Connect your Email")
        st.info("Choose how you want to send emails.")
        
        method = st.radio(
            "Select Email Service:",
            ["Gmail (Browser) - Recommended", "Outlook SMTP (Requires Password)", "Outlook Desktop (Windows Only)"],
            index=0
        )
        
        if method == "Outlook Desktop (Windows Only)" and not LOCAL_OUTLOOK_AVAILABLE:
            st.error("❌ Outlook Desktop is not available on this server/machine.")
        
        if st.button("Connect & Continue"):
            if method == "Outlook Desktop (Windows Only)" and not LOCAL_OUTLOOK_AVAILABLE:
                st.error("Cannot select Outlook Desktop on this environment.")
            else:
                st.session_state.email_method = method
                st.session_state.step = 2
                st.rerun()

    # Step 2: Application Logic
    elif st.session_state.step == 2:
        render_application_page()

def render_application_page():
    # Show connected status in sidebar
    with st.sidebar:
        st.success(f"✅ Connected: {st.session_state.email_method}")
        if st.button("Change Email Method"):
            st.session_state.step = 1
            st.rerun()
        st.divider()

        st.header("Setup & Instructions")
        email_method = st.session_state.email_method
        
        if email_method == "Outlook Desktop (Windows Only)":
            st.info(
                """
                **Requirements:**
                1. Classic Outlook installed & open.
                2. Logged in as your sender account.
                """
            )
        elif email_method == "Outlook SMTP (Requires Password)":
             st.info(
                """
                **Requirements:**
                1. Set `OUTLOOK_EMAIL` in `.env`.
                2. Set `OUTLOOK_PASSWORD` in `.env`.
                3. **Note:** If 2FA is on, use an **App Password**.
                """
            )
        else:
            st.info("Uses your browser's Gmail session. No password required.")

        if not os.path.exists(".env"):
            st.warning("⚠️ .env file not found!")

    # Input Section
    st.subheader("1. Job Details & Resumes")
    
    job_description = st.text_area("Paste Job Description here:", height=200)

    # Resume Upload Section
    st.write("Upload your resumes (PDF only). You can upload multiple files.")
    uploaded_resumes = st.file_uploader("Upload Resumes", type=["pdf"], accept_multiple_files=True)
    
    # Check for resumes in 'resumes' folder
    resumes_dir = "resumes"
    if not os.path.exists(resumes_dir):
        os.makedirs(resumes_dir)
        
    local_resume_files = [f for f in os.listdir(resumes_dir) if f.lower().endswith('.pdf')]
    
    selected_resumes = {} # Dict to store filename: file_content (bytes or path)

    # 1. Add uploaded resumes
    if uploaded_resumes:
        for uploaded_file in uploaded_resumes:
            # Save to disk for persistence across reloads
            save_path = os.path.join(resumes_dir, uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            selected_resumes[uploaded_file.name] = save_path # Use the saved path
            
    # Refresh local list after saving uploads
    local_resume_files = [f for f in os.listdir(resumes_dir) if f.lower().endswith('.pdf')]

    # 2. Add local resumes (checkbox selection or auto-include)
    if local_resume_files:
        st.info(f"files found in '{resumes_dir}' folder: {', '.join(local_resume_files)}")
        use_local = st.checkbox("Include resumes from 'resumes' folder?", value=True)
        if use_local:
            for f_name in local_resume_files:
                selected_resumes[f_name] = os.path.join(resumes_dir, f_name)

    if not selected_resumes:
         st.warning("Please upload resumes or place them in the 'resumes' folder.")

    if "email_data" not in st.session_state:
        st.session_state.email_data = None

    # Generate Email Button
    if st.button("Next: Match Resume & Generate Email"):
        if not job_description:
            st.error("Please paste a job description.")
        elif not selected_resumes:
            st.error("Please provide at least one resume.")
        else:
            with st.spinner("Analyzing resumes..."):
                
                # 1. Parse all resumes text
                resume_texts = {} # filename: text
                
                for name, source in selected_resumes.items():
                    # Read content
                    if isinstance(source, str): # File path
                        try:
                            with open(source, "rb") as f:
                                file_bytes = f.read()
                        except Exception as e:
                            st.error(f"Error reading {name}: {e}")
                            continue
                    else: # UploadedFile object
                        source.seek(0)
                        file_bytes = source.read()
                        
                    text = extract_text_from_pdf(file_bytes)
                    if text:
                        resume_texts[name] = text

                if not resume_texts:
                    st.error("Could not extract text from any resume.")
                    return

                # 2. Find Best Match
                if len(resume_texts) > 1:
                    st.info("Comparing resumes against Job Description...")
                    match_result = find_best_resume(job_description, resume_texts)
                    best_resume_name = match_result.get("best_resume_filename")
                    match_reason = match_result.get("reason")
                    
                    if best_resume_name and best_resume_name in resume_texts:
                        st.success(f"**Best Match Selected:** {best_resume_name}")
                        st.caption(f"Reason: {match_reason}")
                        final_resume_text = resume_texts[best_resume_name]
                        final_resume_name = best_resume_name
                        # Keep track of the file bytes for attachment later
                        # We need to retrieve the original 'source' for the attachment
                        final_resume_source = selected_resumes[best_resume_name] 
                    else:
                        st.error("Could not identify best resume. Defaulting to first one.")
                        first_key = next(iter(resume_texts))
                        final_resume_text = resume_texts[first_key]
                        final_resume_name = first_key
                        final_resume_source = selected_resumes[first_key]
                else:
                    # Only one resume
                    final_resume_name = next(iter(resume_texts))
                    final_resume_text = resume_texts[final_resume_name]
                    final_resume_source = selected_resumes[final_resume_name]
                    st.info(f"Using resume: {final_resume_name}")


                # 3. Extract Recruiter Email (if any)
                recruiter_email = extract_email(job_description)
                
                # 4. Generate Email Content
                email_content = generate_job_application_email(job_description, final_resume_text)
                
                # Prepare bytes for attachment specifically for the selected resume
                if isinstance(final_resume_source, str):
                     with open(final_resume_source, "rb") as f:
                        final_resume_bytes = f.read()
                else:
                    final_resume_source.seek(0)
                    final_resume_bytes = final_resume_source.read()

                # Store in session state
                st.session_state.email_data = {
                    "recruiter_email": recruiter_email,
                    "generated_email": email_content,
                    "resume_name": final_resume_name,
                    "resume_bytes": final_resume_bytes # Store bytes for attachment
                }


    # Display Generated Email Section
    if st.session_state.email_data:
        data = st.session_state.email_data
        st.divider()
        st.subheader("2. Review & Send Email")
        
        email_json = data["generated_email"]

        # Inferred Job Title
        job_title_extracted = email_json.get("job_title", "Job Application")
        st.info(f"**Target Role:** {job_title_extracted}")

        # Recruiter Email Input
        recipient_email = st.text_input(
            "Recruiter's Email:", 
            value=data["recruiter_email"] if data["recruiter_email"] else ""
        )
        
        # Subject Line Input
        subject = st.text_input("Subject:", value=email_json.get("subject", ""))
        
        # Body Input (Text Area)
        body = st.text_area("Email Body:", value=email_json.get("body", ""), height=300)
        
        st.download_button(
            label="Download Email Text",
            data=f"Subject: {subject}\n\n{body}",
            file_name="email_draft.txt",
            mime="text/plain"
        )
        
        st.divider()
        st.write(f"**Attachment:** {data['resume_name']}")

        st.divider()
        st.subheader("3. Select Sending Option")
        
        col1, col2 = st.columns(2)
        
        with col1:
             # Gmail Direct Link
            gmail_url = create_gmail_url(recipient_email, subject, body)
            st.link_button("📤 Open in Gmail (Browser)", gmail_url, help="Opens a new tab in your Gmail with the email ready to send.")

        with col2:
            # Send Button
            if st.button("📧 Send via App (Configuration Required)"):
                if not recipient_email:
                    st.error("Please enter a recipient email address.")
                else:
                    with st.spinner("Sending email..."):
                        try:
                            # Create a temporary file for the resume attachment
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(data["resume_bytes"])
                                temp_resume_path = tmp.name
                            
                            success = False
                            msg = ""

                            if email_method == "Outlook Desktop (No Password)":
                                success, msg = send_email_via_local_outlook(
                                    to_email=recipient_email,
                                    subject=subject,
                                    body=body,
                                    attachment_path=temp_resume_path
                                )
                            else:
                                success, msg = send_email_via_outlook(
                                    to_email=recipient_email,
                                    subject=subject,
                                    body=body,
                                    attachment_bytes=data["resume_bytes"],
                                    attachment_name=data["resume_name"]
                                )

                            # Clean up temp file
                            if os.path.exists(temp_resume_path):
                                os.unlink(temp_resume_path)

                            if success:
                                st.success(f"✅ Email sent successfully to {recipient_email}!")
                                save_to_excel(job_title_extracted, recipient_email)
                                st.balloons()
                            else:
                                st.error(f"❌ Failed to send email: {msg}")

                        except Exception as e:
                            st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()

    # Sidebar Footer: Data Download
    with st.sidebar:
        st.divider()
        st.subheader("📊 Application Tracker")
        tracker_file = "job_application_tracker.xlsx"
        if os.path.exists(tracker_file):
            with open(tracker_file, "rb") as f:
                st.download_button(
                    label="Download Excel Tracker",
                    data=f,
                    file_name="job_applications.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.caption("No applications tracked yet.")
