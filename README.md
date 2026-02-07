# AI Job Application Assistant

This is an end-to-end AI-powered application that generates and sends professional job application emails. It uses Streamlit for the frontend, OpenAI for email generation, and the Gmail API for sending emails.

## Prerequisites

- Python 3.8+
- A Groq API Key
- An Outlook account (Email & Password)

## Setup Instructions

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**
    - Create a `.env` file in the root directory.
    - Add your keys:
      ```
      GROQ_API_KEY=gsk_your_groq_key_here
      OUTLOOK_EMAIL=your_email@outlook.com
      OUTLOOK_PASSWORD=your_password
      ```
    - **Note**: If you have 2-Factor Authentication enabled on Outlook, you must generate an **App Password** and use that instead of your regular password.

## Running the Application

```bash
streamlit run app.py
```

## Usage

1.  The application will open in your browser.
2.  Paste the **Job Description** into the text area.
3.  Upload your **Resume (PDF)**.
4.  Click **Next: Generate Email**.
    -   The AI will analyze the resume and job description.
5.  Review the generated email.
6.  Click **Send Email via Outlook**.

## Troubleshooting

-   **SMTP Error**: If sending fails, check your internet connection and ensure your Outlook credentials in `.env` are correct.
-   **Blocked Sign-in**: Microsoft might block the sign-in if it looks suspicious. Check your email for security alerts or use an App Password.
