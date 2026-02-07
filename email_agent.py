import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
    Your task is to write a professional job application email based on a candidate's resume and a job description.
    
    Follow these rules strictly:
    1. Tone: Professional, corporate, confident but humble.
    2. Length: 150–250 words (slightly longer to accommodate projects).
    3. Structure:
       - **Salutation**: Professional greeting.
       - **Opening**: State the specific role you are applying for.
       - **Value Proposition**: Briefly summarize your experience and key skills matching the JD.
       - **Key Projects**: **CRITICAL:** You MUST explicitly mention 3 key projects. **Do NOT use asterisks (*) for bullet points.** Use simple dashes (-) or write in a cohesive paragraph.
       - **Resume Reference**: Mention the attached resume.
       - **Closing**: Professional sign-off.
    4. Formatting: 
       - **ABSOLUTELY NO asterisks (*)** anywhere in the body.
       - No emojis.
       - Use clear paragraph breaks (double newlines).
       - Proper greeting (e.g., "Dear Hiring Manager," or specific name if found).
       - **Sign-off**: Use a professional sign-off. Extract the candidate's name, email, and LinkedIn/GitHub (if available) from the resume to create the signature. Do NOT make up contact details. If not found, use placeholders like "[Candidate Name]".

    5. Output Format: Return valid JSON with three keys: "subject", "body", and "job_title".
       - "subject": A concise, professional subject line.
       - "body": The plain text body of the email.
       - "job_title": The Job Title extracted from the Job Description. If not explicitly stated, infer it.
    """
    
    user_prompt = f"""
    JOB DESCRIPTION:
    {job_description}
    
    RESUME CONTENT:
    {resume_text}
    
    Generate the email in JSON format.
    """
    
    try:
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
