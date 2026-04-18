import json
import os
from typing import Any, Dict, List

from openai import OpenAI


_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def generate(
    spec_text: str,
    repair_contract: List[Dict[str, Any]],
    allowed_files: List[str],
) -> Dict[str, str]:

    client = _get_client()

    # SAFE minimal call (no complex schema assumptions)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        input="Return JSON: {\"files\": []}"
    )

    text = response.choices[0].message.content

    try:
        payload = json.loads(text)
    except Exception:
        return {}

    return {}
