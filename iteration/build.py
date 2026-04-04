import traceback
from engine.llm_interface import generate_code
from engine.file_writer import write_app


def build_system(spec: dict):
    logs = []

    try:
        try:
            code = generate_code(spec)
            logs.append("Code generated")
        except Exception as e:
            return {
                "status": "failure",
                "logs": [f"LLM FAILURE: {str(e)}"]
            }

        # Empty or bad response protection
        if not code or len(code.strip()) < 20:
            return {
                "status": "failure",
                "logs": ["LLM returned empty or invalid code"]
            }

        # Ensure FastAPI presence (minimal guard)
        if "FastAPI" not in code:
            return {
                "status": "failure",
                "logs": ["Generated code missing FastAPI"]
            }

        # Compile check (real validation)
        try:
            compile(code, "<generated_app>", "exec")
        except Exception as e:
            return {
                "status": "failure",
                "logs": [f"Syntax error: {str(e)}"]
            }

        path = write_app(code)
        logs.append(f"Code written to {path}")

        return {
            "status": "success",
            "logs": logs
        }

    except Exception as e:
        return {
            "status": "failure",
            "logs": [
                f"UNEXPECTED BUILD ERROR: {str(e)}",
                traceback.format_exc()
            ]
        }
