import json
from datetime import datetime, timezone
from pathlib import Path
def generate_audit_report(run_id: str, result: Dict[str, Any]) -> str:
    report = {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(), "authority": "Formal Technical specification for Autonomous SW factory v 2.1", "result": result, "ku_model": {"Normative": "static", "Dynamic": "evolving"}, "er_model": {"Entity": "Project", "Relationship": "Run", "Policy_Set": "Budget_Policy"}, "test_layers_passed": result.get("result", {}).get("test_layers", 0), "convergence_history": result.get("iteration", 0)}
    path = f"reports/audit_{run_id}.json"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(report, f, indent=2)
    return path
