import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# client initialized lazily inside function to avoid startup crashes if env var is missing

def generate_job_application_email(job_description: str, resume_text: str):
    """
    Generates a professional job application email using OpenAI.
    
    Args:
        job_description (str): The text of the job description.
        resume_text (str): The text extracted from the user's resume.
        
    Returns:
        dict: A dictionary containing 'subject' and 'body' of the email.
    """
    
    system_prompt = """
    You are a professional career coach and expert copywriter. 
    Your task is to write a SHORT, IMPACTFUL job application email based on a candidate's resume and a job description.
    
    CRITICAL RULES:
    1. **ONLY USE INFORMATION FROM THE RESUME** - Do NOT invent or add any skills, projects, technologies, or experience that is NOT explicitly mentioned in the resume.
    2. **Match JD with Resume** - Identify which skills/projects from the RESUME align with the Job Description. Only highlight those.
    3. **If a JD requirement is NOT in the resume** - Do NOT mention it. Do NOT pretend the candidate has that skill.
    
    Follow these rules strictly:
    1. Tone: Professional, confident, concise. HR-friendly and attention-grabbing.
    2. Length: **100-150 words MAXIMUM**. Short and crisp. No fluff.
    3. Structure:
       - **Salutation**: "Dear Hiring Manager," (or name if found in JD)
       - **Opening**: One line stating the role you're applying for.
       - **Value Proposition**: 2-3 sentences highlighting ONLY relevant skills/experience FROM THE RESUME that match the JD.
       - **Key Project**: Mention 1-2 relevant projects FROM THE RESUME only. Keep it brief.
       - **Closing**: One line about attached resume + call to action.
       - **Sign-off**: Professional closing.
    4. Formatting: 
       - **NO asterisks (*)** anywhere.
       - No emojis.
       - Short paragraphs.
       - **Signature**: Include these links:
         LinkedIn: https://www.linkedin.com/in/syedmuhammadmuzammil077/
         GitHub: https://github.com/Muhammad-Muzammil-Shah

    5. Output Format: Return valid JSON with three keys: "subject", "body", and "job_title".
       - "subject": Short, professional subject line (max 10 words).
       - "body": The plain text body of the email.
       - "job_title": The Job Title from the JD.
    """
    
    user_prompt = f"""
    JOB DESCRIPTION:
    {job_description}
    
    RESUME CONTENT:
    {resume_text}
    
    Generate the email in JSON format.
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
            model="llama-3.3-70b-versatile", # Using Groq's Llama 3.3 70B model
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
