import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# client initialized lazily inside function to avoid startup crashes if env var is missing

def generate_job_application_email(job_description: str, resume_text: str, github_projects=None):
    """
    Generates a professional job application email using Groq AI.
    Deeply analyzes JD + Resume + GitHub projects to create a tailored email.
    """

    system_prompt = """
    You are an elite Executive Recruiter and Career Strategist. 
    Your mission is to write a compelling, high-impact job application email that stands out in a crowded inbox.

    CORE PRINCIPLE:
    - **AUTHENTICITY**: The email must sound like it was written by a thoughtful professional, not an AI.
    - **RESULT-DRIVE**: Focus on what you can DO for the company, not just what you know.
    - **NO MARKDOWN**: Absolutely no stars (*), double stars (**), or symbols. Use standard indentation and capitalization.

    YOUR APPROACH:
    1. Identify the core challenge or requirement in the JD.
    2. Select the most impressive evidence from the Resume and GitHub that solves that challenge.
    3. Bridge them with a sophisticated, professional narrative.

    EMAIL STRUCTURE:
    1. **Subject**: Professional, concise, and role-specific.
    2. **Salutation**: "Dear [Hiring Manager/Recruiter Name/Team Name],"
    3. **Opening Paragraph**: A concise introduction stating the specific role and your high-level interest in [Company Name]. 
    4. **The Value Pitch**: One strong, fluid paragraph that weaves together your professional background with relevant project work. Highlight impact (e.g., "leveraged [skill] to build [GitHub project], achieving [result]").
    5. **Project/Achievement Highlights**: If specific projects are highly relevant, list them using simple, clean dashes (-). 
       Format: Project Name - One sentence explaining the technical impact or problem solved. (No bolding, no stars).
    6. **The Closing**: A confident, professional closing that invites further discussion about how your background aligns with their goals.
    7. **Signature**: Formal closing (e.g., "Sincerely,", "Best regards,") followed by name and links.

    TONE & STYLE:
    - **Tone**: Professional, confident, and respectful (Executive level).
    - **Clarity**: Use active verbs and avoid fluff. 
    - **Formatting**: Plain text only. Use standard paragraph spacing (double line breaks).
    - **Signature Links**: Always include these in the sign-off:
        LinkedIn: https://www.linkedin.com/in/syedmuhammadmuzammil077/
        GitHub: https://github.com/Muhammad-Muzammil-Shah

    OUTPUT FORMAT: Return valid JSON with:
    - "subject": Professional subject line.
    - "body": The plain text email body.
    - "job_title": The Job Title.
    - "company_name": The Company Name.
    """

    user_prompt = f"""
    ===== JOB DESCRIPTION =====
    {job_description}

    ===== CANDIDATE'S RESUME =====
    {resume_text}

    ===== CANDIDATE'S GITHUB PROJECTS (Top Relevant) =====
    {json.dumps(github_projects, ensure_ascii=False, indent=2) if github_projects else 'None provided'}

    ===== TASK =====
    Analyze all three sources above. Find the overlapping skills/experience between JD, Resume, and GitHub.
    Write a professional email that demonstrates the candidate is a strong match.
    Return JSON with "subject", "body", and "job_title".
    """

    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {
                "subject": "Configuration Error",
                "body": "GROQ_API_KEY environment variable is missing. Please add it to your Azure Configuration."
            }

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" }
        )

        content = response.choices[0].message.content
        # Remove potential markdown code blocks
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        elif content.startswith("```"):
            content = content.replace("```", "")

        return json.loads(content)

    except Exception as e:
        print(f"Error generating email: {e}")
        return {
            "subject": "Error generating email",
            "body": f"An error occurred while generating the email. Please check your logs or try again.\nError: {e}"
        }
