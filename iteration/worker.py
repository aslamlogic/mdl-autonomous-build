from __future__ import annotations

from typing import Dict, Any

from iteration.controller import IterationController


def execute_run(workspace_path: str, initial_spec_text: str, run_id: str = "default_run") -> Dict[str, Any]:
    controller = IterationController()
    return controller.run(
        workspace_path=workspace_path,
        initial_spec_text=initial_spec_text,
        run_id=run_id
    )
