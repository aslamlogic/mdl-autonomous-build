import os
from openai import OpenAI
def generate(prompt, **kwargs):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
    return {"status":"success", "content": res.choices[0].message.content}