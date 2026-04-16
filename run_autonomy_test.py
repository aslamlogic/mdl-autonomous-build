
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
