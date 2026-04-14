import os
import re
import uuid
import importlib.util
from pathlib import Path
from typing import Optional

from openai import OpenAI


GENERATED_DIR = Path("generated_apps")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _extract_python_code(text: str) -> str:
    """
    Extract Python code from raw model output.
    Accepts either plain code or fenced code blocks.
    """
    if not text or not text.strip():
        raise ValueError("Model returned empty output")

    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        code = fenced.group(1).strip()
    else:
        code = text.strip()

    if not code:
        raise ValueError("No Python code found in model output")

    return code


def _build_generation_prompt(user_prompt: str) -> str:
    """
    Wrap the incoming prompt with hard generation constraints so the
    returned code is directly importable and produces a valid FastAPI app.
    """
    return f"""
You are generating a single Python module.

Return ONLY executable Python code.
Do not return markdown.
Do not return explanations.
Do not return comments unless required in the code itself.

Hard requirements:
1. The module MUST import FastAPI from fastapi.
2. The module MUST define: app = FastAPI()
3. The module MUST expose `app` as the ASGI callable.
4. The module MUST implement GET /health
5. GET /health MUST return {{"status": "ok"}}
6. The module must be self-contained and importable.
7. Do not use placeholders.
8. Do not wrap the code in backticks.

Generation context:
{user_prompt}
""".strip()


def _request_code_from_model(prompt: str, model: Optional[str] = None) -> str:
    """
    Call OpenAI and return raw text output.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    chosen_model = model or DEFAULT_MODEL

    response = client.chat.completions.create(
        model=chosen_model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a deterministic Python code generator. "
                    "Return only executable Python source."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("Model returned no content")

    return content


def _write_generated_module(code: str) -> Path:
    """
    Persist generated code to a unique module path.
    """
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    module_name = f"generated_app_{uuid.uuid4().hex}"
    module_path = GENERATED_DIR / f"{module_name}.py"
    module_path.write_text(code, encoding="utf-8")
    return module_path


def _load_module_from_path(module_path: Path):
    """
    Dynamically import the generated module from disk.
    """
    module_name = module_path.stem
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create import spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_app(module):
    """
    Extract and validate the generated FastAPI app object.
    """
    if not hasattr(module, "app"):
        raise RuntimeError("Generated module does not define `app`")

    app = module.app

    if not callable(app):
        raise RuntimeError("Generated `app` is not callable")

    return app


def generate_code(prompt: str):
    """
    Generate Python code from the prompt, write it to disk, import it,
    extract `app`, and return the ASGI application object.
    """
    wrapped_prompt = _build_generation_prompt(prompt)
    raw_output = _request_code_from_model(wrapped_prompt)
    code = _extract_python_code(raw_output)
    module_path = _write_generated_module(code)
    module = _load_module_from_path(module_path)
    app = _extract_app(module)
    return app
