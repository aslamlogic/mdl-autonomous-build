from typing import Dict, Any
def enforce_budget_routing(spec: Dict[str, Any]) -> bool:
    budget = spec.get("Budget_Policy", {})
    routing = spec.get("Routing_Policy", {})
    if budget.get("max_iterations", 5) < 1: return False
    if routing.get("provider", "render") not in ["render", "railway", "github"]: return False
    return True
