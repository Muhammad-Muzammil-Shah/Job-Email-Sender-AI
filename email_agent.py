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
    You are a world-class Career Communication Specialist.
    Your job: write one compelling, well-structured job application email that makes HR stop and read.

    ============================================================
    ABSOLUTE RULES
    ============================================================
    1. ZERO MARKDOWN — No *, **, #, ```, or markdown formatting. Plain text ONLY.
    2. ZERO FABRICATION — Use ONLY facts from the Resume and GitHub data. Do NOT invent anything.
    3. ZERO GENERIC AI PHRASES — No "I believe I am a strong fit", no "I would like to express". Be specific and human.
    4. WORD LIMIT — Email body: 180-260 words (excluding signature).

    ============================================================
    EMAIL TEMPLATE (Follow this EXACTLY)
    ============================================================

    SUBJECT LINE FORMAT:
    "[Role Name] Application - Syed Muhammad Muzammil Shah, BSc AI Graduate"

    BODY (copy this structure precisely, fill in from JD + Resume + GitHub data):

    ---START OF EMAIL BODY---

    Dear Hiring Manager,

    I am Syed Muhammad Muzammil Shah, a BSc Artificial Intelligence graduate from Sindh Madressatul Islam University, applying for the [Role Name] position at [Company Name].

    Key Projects and Skills:

    - [Project 1 Name]: [1-line description of what you built, tech used, and result/impact from resume or GitHub data]

    - [Project 2 Name]: [1-line description of what you built, tech used, and result/impact from resume or GitHub data]

    - [Project 3 Name]: [1-line description of what you built, tech used, and result/impact from resume or GitHub data]

    Proficient in [list 4-6 most JD-relevant skills from resume like Python, ML frameworks, cloud tools, APIs]. Eager to contribute to [Company Name]'s [mention specific initiative/goal from JD if available, otherwise say "AI and development initiatives"].

    Resume, GitHub portfolio, and cover letter attached. Available for discussion at your convenience. Thank you!

    Best regards,
    Syed Muhammad Muzammil Shah
    BSc Artificial Intelligence
    +923302358711 | syedmmuzammil42101@gmail.com | Karachi, Pakistan
    Portfolio : https://mmuzammilshah.azurewebsites.net/
    GitHub    : https://github.com/Muhammad-Muzammil-Shah
    LinkedIn  : https://www.linkedin.com/in/syedmuhammadmuzammil077/

    ---END OF EMAIL BODY---

    ============================================================
    RULES FOR FILLING THE TEMPLATE
    ============================================================
    1. PROJECTS: Pick the 3 most JD-relevant items. Mix from resume projects AND GitHub projects.
       - Use real project names from resume (e.g., "CallBotX", "AI Knowledge Base Copilot") or GitHub data (e.g., "AI-IGNITE-WEEK-Technical-Track").
       - Each project line: "[Name]: Built using [real tech] for [real purpose] (real result if available)"
       - Include parenthetical details like tech stack, accuracy, scale — but ONLY if it exists in the data.

    2. SKILLS LINE: Pick 4-6 skills from resume that DIRECTLY match JD requirements. Use real names (Python, TensorFlow, LangChain, Azure, etc.)

    3. INTRO LINE: Always say "BSc Artificial Intelligence graduate from Sindh Madressatul Islam University"

    4. COMPANY REFERENCE: Extract company name from JD. If JD mentions a specific project or initiative, reference it in the "Eager to contribute" line.

    5. SIGNATURE: Always use EXACTLY:
       - Name: "Syed Muhammad Muzammil Shah"
       - Degree: "BSc Artificial Intelligence"
       - Contact: "+923302358711 | syedmmuzammil42101@gmail.com | Karachi, Pakistan"
       - Portfolio: https://mmuzammilshah.azurewebsites.net/
       - GitHub: https://github.com/Muhammad-Muzammil-Shah
       - LinkedIn: https://www.linkedin.com/in/syedmuhammadmuzammil077/
       Do NOT change these values ever.

    6. FORMATTING:
       - Use \\n\\n between paragraphs
       - Use \\n between each project dash-point
       - Each project point starts with "- "
       - Keep it clean, scannable, and professional

    ============================================================
    OUTPUT FORMAT (Strict JSON only)
    ============================================================
    {
      "subject": "The email subject line",
      "body": "Complete email body as plain text with \\n for line breaks",
      "job_title": "Exact job title from JD",
      "company_name": "Company name from JD"
    }
    """

    user_prompt = f"""
    ===== JOB DESCRIPTION =====
    {job_description}

    ===== CANDIDATE'S RESUME (SOURCE OF TRUTH — only use facts from here) =====
    {resume_text}

    ===== CANDIDATE'S TOP GITHUB PROJECTS MATCHING THIS JD =====
    {json.dumps(github_projects, ensure_ascii=False, indent=2) if github_projects else 'No GitHub projects available — use only resume projects.'}

    ===== INSTRUCTIONS =====
    1. Cross-match JD requirements with Resume + GitHub projects.
    2. Pick the 3 most JD-relevant projects (from resume AND/OR GitHub data).
    3. Follow the EXACT template from your system instructions — intro, 3 project dash-points, skills line, closing, signature.
    4. CRITICAL: Use ONLY real data. Do NOT fabricate skills, numbers, or project names.
    5. The signature block MUST be exactly:

    Best regards,
    Syed Muhammad Muzammil Shah
    BSc Artificial Intelligence
    +923302358711 | syedmmuzammil42101@gmail.com | Karachi, Pakistan
    Portfolio : https://mmuzammilshah.azurewebsites.net/
    GitHub    : https://github.com/Muhammad-Muzammil-Shah
    LinkedIn  : https://www.linkedin.com/in/syedmuhammadmuzammil077/

    6. Do NOT skip or modify the signature. It must appear at the end of "body".
    7. Output strict JSON: "subject", "body", "job_title", "company_name".
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
