import json
import os
from datetime import datetime
from typing import Dict, Any, List


class ReportBuilder:
    """
    Builds validation and audit reports.
    """

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    def build_validation_report(self, run_id: str, passed: bool, findings: List[Dict[str, Any]]) -> str:
        report = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "passed": passed,
            "finding_count": len(findings),
            "findings": findings
        }
        path = os.path.join(self.reports_dir, f"validation_{run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return path

    def build_audit_report(self, run_id: str, summary: Dict[str, Any]) -> str:
        path = os.path.join(self.reports_dir, f"audit_{run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        return path
