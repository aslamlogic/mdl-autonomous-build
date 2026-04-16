import os
import subprocess
from textwrap import dedent


def write_file(path: str, content: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n")
    print(f"UPDATED: {path}")


LLM_INTERFACE = dedent(
    '''
    import json
    import os
    from typing import Any, Dict, List

    from openai import OpenAI


    def _get_client() -> OpenAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return OpenAI(api_key=api_key)


    def _system_message() -> str:
        return """
    You are a deterministic multi-file repair engine.

    HARD RULES:
    1. Return only strict JSON.
    2. JSON schema:
       {
         "files": [
           {"path": "<allowed path>", "content": "<full file content>"}
         ]
       }
    3. Only create or modify files listed in allowed_files.
    4. Do not emit markdown fences.
    5. Do not emit explanations.
    6. Prefer the minimum changes needed to satisfy the repair contract.
    7. If a file is not required for repair, do not include it.
    """


    def _user_message(
        spec_text: str,
        repair_contract: List[Dict[str, Any]],
        allowed_files: List[str],
    ) -> str:
        return f"""
    BASE_SPEC:
    {spec_text}

    ALLOWED_FILES:
    {json.dumps(allowed_files, indent=2)}

    REPAIR_CONTRACT:
    {json.dumps(repair_contract, indent=2)}

    OUTPUT:
    Return strict JSON only.
    """


    def _strip_fences(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3].strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return cleaned


    def _validate_payload(payload: Dict[str, Any], allowed_files: List[str]) -> Dict[str, str]:
        files = payload.get("files")
        if not isinstance(files, list):
            raise RuntimeError("LLM payload missing files list")

        result: Dict[str, str] = {}
        for item in files:
            if not isinstance(item, dict):
                raise RuntimeError("LLM payload file entry is not an object")

            path = item.get("path")
            content = item.get("content")

            if not isinstance(path, str) or not path:
                raise RuntimeError("LLM payload file path is invalid")
            if path not in allowed_files:
                raise RuntimeError(f"LLM attempted forbidden file path: {path}")
            if not isinstance(content, str):
                raise RuntimeError(f"LLM payload content invalid for: {path}")

            result[path] = content

        return result


    def generate(
        spec_text: str,
        repair_contract: List[Dict[str, Any]],
        allowed_files: List[str],
    ) -> Dict[str, str]:
        client = _get_client()

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            messages=[
                {"role": "system", "content": _system_message()},
                {"role": "user", "content": _user_message(spec_text, repair_contract, allowed_files)},
            ],
        )

        content = response.choices[0].message.content
        if not content or not isinstance(content, str):
            raise RuntimeError("LLM returned empty content")

        cleaned = _strip_fences(content)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM did not return valid JSON: {e}") from e

        return _validate_payload(payload, allowed_files)
    '''
)

SPEC_UPDATER = dedent(
    '''
    from typing import Any, Dict, List


    class SpecUpdater:
        FAILURE_TO_ACTION = {
            "E-SYNTAX": "fix_syntax",
            "E-DEPENDENCY": "fix_dependency",
            "E-STRUCTURE": "create_or_fix_structure",
            "E-BEHAVIOUR": "fix_runtime_behaviour",
            "E-SCHEMA": "fix_schema",
            "E-GOVERNANCE": "fix_governance",
            "E-SECURITY": "fix_security",
            "E-LWP": "restore_lwp_chain",
            "E-UI": "restore_ui_markers",
            "E-SPEC-UNDERDETERMINED": "stay_within_explicit_scope",
            "E-UNKNOWN": "fix_conservatively",
        }

        FAILURE_TO_GUIDANCE = {
            "E-SYNTAX": "Correct syntax without rewriting unrelated logic.",
            "E-DEPENDENCY": "Resolve imports and declarations without introducing undeclared dependencies.",
            "E-STRUCTURE": "Create missing required files or directories and populate them minimally but validly.",
            "E-BEHAVIOUR": "Implement the required endpoint or runtime behaviour exactly.",
            "E-SCHEMA": "Correct schema mismatch without weakening validation.",
            "E-GOVERNANCE": "Remove prohibited patterns and preserve deterministic execution.",
            "E-SECURITY": "Remove insecure patterns and replace them conservatively.",
            "E-LWP": "Create or repair the rule application path required for deterministic LWP validation.",
            "E-UI": "Create or repair the minimum UI markers or files required by validation.",
            "E-SPEC-UNDERDETERMINED": "Do not invent extra features beyond explicit requirements.",
            "E-UNKNOWN": "Apply the smallest safe correction to the flagged issue.",
        }

        def derive_constraints(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            repair_contract: List[Dict[str, Any]] = []

            for finding in findings:
                failure_code = str(finding.get("failure_code", "E-UNKNOWN"))
                message = str(finding.get("message", "")).strip()
                path = str(finding.get("path", "")).strip()

                repair_contract.append(
                    {
                        "failure_code": failure_code,
                        "path": path,
                        "action": self.FAILURE_TO_ACTION.get(failure_code, "fix_conservatively"),
                        "guidance": self.FAILURE_TO_GUIDANCE.get(
                            failure_code,
                            self.FAILURE_TO_GUIDANCE["E-UNKNOWN"],
                        ),
                        "message": message,
                        "forbidden_regressions": [
                            "Do not modify files outside allowed_files.",
                            "Do not remove a valid /health endpoint.",
                            "Do not add markdown or commentary into source files.",
                            "Do not replace multi-file output with single-file output.",
                        ],
                    }
                )

            return repair_contract
    '''
)

CONTROLLER = dedent(
    '''
    import os
    from typing import Any, Dict, List, Set

    from engine.llm_interface import generate
    from iteration.evaluator import evaluate
    from iteration.spec_updater import SpecUpdater


    class IterationController:
        def __init__(self, max_iterations: int = 5):
            self.max_iterations = max_iterations
            self.spec_updater = SpecUpdater()

        def _allowed_files(self) -> List[str]:
            return [
                "generated_app/main.py",
                "meta_ui/api.py",
                "iteration/controller.py",
                "iteration/rule_applicator.py",
                "apps/__init__.py",
            ]

        def _full_path(self, workspace_path: str, relative_path: str) -> str:
            return os.path.join(workspace_path, relative_path)

        def _write_files(self, workspace_path: str, files: Dict[str, str]) -> None:
            for relative_path, content in files.items():
                full_path = self._full_path(workspace_path, relative_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

        def _score(self, result: Dict[str, Any]) -> int:
            findings = result.get("findings", []) or []
            passed = bool(result.get("passed", False))
            return (10 if passed else 0) - len(findings)

        def _failure_signature(self, result: Dict[str, Any]) -> Set[str]:
            findings = result.get("findings", []) or []
            signature: Set[str] = set()
            for finding in findings:
                code = str(finding.get("failure_code", "E-UNKNOWN"))
                path = str(finding.get("path", ""))
                message = str(finding.get("message", ""))
                signature.add(f"{code}|{path}|{message}")
            return signature

        def run(self, workspace_path: str, initial_spec_text: str, run_id: str = "run") -> Dict[str, Any]:
            previous_score = None
            previous_signature: Set[str] = set()
            repair_contract: List[Dict[str, Any]] = []
            allowed_files = self._allowed_files()

            for iteration_index in range(self.max_iterations):
                print(f"ITERATION {iteration_index}")

                generated_files = generate(
                    spec_text=initial_spec_text,
                    repair_contract=repair_contract,
                    allowed_files=allowed_files,
                )

                self._write_files(workspace_path, generated_files)

                main_path = self._full_path(workspace_path, "generated_app/main.py")
                main_content = ""
                if os.path.exists(main_path):
                    with open(main_path, "r", encoding="utf-8") as f:
                        main_content = f.read()

                result = evaluate(main_content)
                score = self._score(result)
                print(f"Score: {score}")

                if result.get("passed", False):
                    print("VALIDATED_BUILD")
                    return {
                        "status": "SUCCESS",
                        "score": score,
                        "iteration": iteration_index,
                        "result": result,
                    }

                current_signature = self._failure_signature(result)

                if previous_score is not None and score <= previous_score:
                    print("NO IMPROVEMENT -> STOP")
                    return {
                        "status": "FAIL",
                        "reason": "no_improvement",
                        "score": score,
                        "iteration": iteration_index,
                        "result": result,
                    }

                if previous_signature and current_signature == previous_signature:
                    print("IDENTICAL FAILURE SIGNATURE -> STOP")
                    return {
                        "status": "FAIL",
                        "reason": "identical_failure_signature",
                        "score": score,
                        "iteration": iteration_index,
                        "result": result,
                    }

                repair_contract = self.spec_updater.derive_constraints(result.get("findings", []) or [])
                previous_score = score
                previous_signature = current_signature

            return {
                "status": "FAIL",
                "reason": "max_iterations_reached",
                "iteration": self.max_iterations,
            }
    '''
)

RUN_AUTONOMY_TEST = dedent(
    '''
    from dotenv import load_dotenv
    load_dotenv()

    from iteration.controller import IterationController


    def main():
        controller = IterationController(max_iterations=3)

        spec = """
    Build a FastAPI system with:

    - GET /health endpoint returning {"status": "ok"}

    - Required structure:
      - meta_ui/api.py
      - iteration/controller.py
      - apps/generated_app/main.py
      - iteration/rule_applicator.py
      - apps/__init__.py

    - Must satisfy validation system requirements:
      - structural completeness
      - behaviour compatibility
      - UI markers present
      - deterministic execution
      - deterministic LWP chain support

    - Do not include unnecessary features
    """

        result = controller.run(
            workspace_path=".",
            initial_spec_text=spec,
            run_id="autonomy_test"
        )

        print("FINAL RESULT:", result)


    if __name__ == "__main__":
        main()
    '''
)

write_file("engine/llm_interface.py", LLM_INTERFACE)
write_file("iteration/spec_updater.py", SPEC_UPDATER)
write_file("iteration/controller.py", CONTROLLER)
write_file("run_autonomy_test.py", RUN_AUTONOMY_TEST)

subprocess.run(
    [
        "git",
        "add",
        "engine/llm_interface.py",
        "iteration/spec_updater.py",
        "iteration/controller.py",
        "run_autonomy_test.py",
        "bootstrap_convergence_v3.py",
    ],
    check=True,
)
subprocess.run(["git", "commit", "-m", "Implement convergence v3"], check=True)
subprocess.run(["git", "push"], check=True)

print("CONVERGENCE V3 DEPLOYED")
