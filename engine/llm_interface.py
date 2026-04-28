import os
from openai import OpenAI
from datetime import datetime

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate(prompt: str, repairs: list = None, allowed_files: list = None) -> dict:
    """Fixed LLM call per SMR v5.6 and OpenAI client requirements"""
    print(f"[{datetime.now()}] LLM generate called with prompt length: {len(prompt)}")

    if repairs:
        prompt += "\n\nPrevious repairs attempted: " + str(repairs)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert autonomous software engineer. Follow USS v2.1 and SMR v5.6 strictly. Produce clean, working code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        print(f"[{datetime.now()}] LLM response received ({len(content)} chars)")
        return {"content": content, "status": "success"}
    except Exception as e:
        print(f"LLM Error: {type(e).__name__}: {e}")
        return {"content": f"Error: {str(e)}", "status": "error"}
