import os
import json
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

async def evaluate_resume(resume_text: str, target_role: str):
    """Sends resume text to Groq for ATS scoring."""
    
    system_prompt = (
        "You are an expert ATS (Applicant Tracking System). "
        "Analyze the resume text against the target role. "
        "Return ONLY a JSON object. Do not include any conversational text."
    )
    
    user_prompt = f"""
    Target Role: {target_role}
    Resume Content: {resume_text}
    
    Return JSON structure:
    {{
        "score": 0-100,
        "match_explanation": "short summary",
        "missing_skills": ["skill1", "skill2"],
        "recommended": true/false
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return {"score": 0, "match_explanation": "Error in AI processing."}