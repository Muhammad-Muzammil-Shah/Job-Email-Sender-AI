import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def find_best_resume(job_description: str, resumes: dict) -> dict:
    """
    Analyzes multiple resumes against a job description and selects the best one.
    
    Args:
        job_description (str): The text of the job description.
        resumes (dict): A dictionary where keys are filenames and values are resume text content.
        
    Returns:
        dict: A dictionary containing 'best_resume_filename' and 'reason'.
    """
    
    # helper to format resumes for the prompt
    resumes_text_formatted = ""
    for filename, text in resumes.items():
        # Truncate text to avoid token limits if necessary, but Groq usually handles large context well.
        # Taking first 2000 chars should be enough for a summary match if context is tight, 
        # but let's try sending full text first.
        resumes_text_formatted += f"--- RESUME: {filename} ---\n{text}\n\n"

    system_prompt = """
    You are an expert HR recruiter and technical hiring manager.
    Your task is to analyze a Job Description and a list of candidate resumes.
    You must determine which resume is the BEST fit for the job description based on skills, experience, and keywords.
    
    Output Format:
    Return strictly a JSON object with the following key:
    - "best_resume_filename": The exact filename of the selected resume.
    - "reason": A short explanation of why this resume was chosen.
    """
    
    user_prompt = f"""
    JOB DESCRIPTION:
    {job_description}
    
    CANDIDATE RESUMES:
    {resumes_text_formatted}
    
    Analyze and return the JSON.
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        content = response.choices[0].message.content
        
        if not content:
            raise ValueError("AI returned empty content")

        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        elif content.startswith("```"):
            content = content.replace("```", "")
            
        result = json.loads(content)
        return result
        
    except Exception as e:
        print(f"Error matching resume: {e}")
        # Fallback: return the first filename if error
        first_key = next(iter(resumes)) if resumes else None
        return {"best_resume_filename": first_key, "reason": f"Error in AI matching: {e}. Defaulted to first resume."}
