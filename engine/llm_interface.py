import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def generate_code(spec: dict) -> str:
    if not client:
        raise RuntimeError("OpenAI client not initialised")

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing")

    prompt = f"""
You are a backend generator.

Generate a valid FastAPI app.

Requirements:
- Must define: app = FastAPI()
- Must include at least one endpoint: /health
- Must return JSON

Spec:
{spec}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You generate Python FastAPI code only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("Empty response from OpenAI")

        return content

    except Exception as e:
        raise RuntimeError(f"OpenAI call failed: {str(e)}")
