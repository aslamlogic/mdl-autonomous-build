from typing import Dict, Any


class ConvergenceController:
    """
    Deterministic termination logic for iteration loop.
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations

    def should_terminate(self, iteration_no: int, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        passed = validation_result.get("passed", False)

        if passed:
            return {
                "terminate": True,
                "status": "VALIDATED_BUILD",
                "reason": "Validation passed"
            }

        if iteration_no >= self.max_iterations:
            return {
                "terminate": True,
                "status": "FAIL",
                "reason": "Maximum iterations reached"
            }

        return {
            "terminate": False,
            "status": "CONTINUE",
            "reason": "Validation failed but iteration budget remains"
        }
