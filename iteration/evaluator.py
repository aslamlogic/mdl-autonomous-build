import ast, json, os, re
from typing import Dict, Any, List
def evaluate(main_content: str) -> Dict[str, Any]:
    findings = []
    try:
        if main_content.strip(): ast.parse(main_content)
    except SyntaxError as e: findings.append({"category": "SYNTAX", "message": str(e), "failure_code": "E-SYNTAX"})
    for f in ["meta_ui/api.py", "iteration/controller.py", "apps/__init__.py"]:
        if not os.path.exists(f): findings.append({"category": "STRUCTURE", "message": f"Required file missing: {f}", "failure_code": "E-STRUCTURE"})
    if "/health" not in main_content or "status" not in main_content: findings.append({"category": "BEHAVIOUR", "message": "Required /health endpoint missing", "failure_code": "E-BEHAVIOUR"})
    for p in [r"subprocess", r"eval\s*\(", r"exec\s*\(", r"os\.system", r"shell\s*=\s*True"]:
        if re.search(p, main_content): findings.append({"category": "GOVERNANCE", "message": f"Prohibited pattern: {p}", "failure_code": "E-GOVERNANCE"})
    for p in [r"requests\.", r"OPENAI_API_KEY\s*=\s*["']", r"GITHUB_TOKEN\s*=\s*["']"]:
        if re.search(p, main_content): findings.append({"category": "SECURITY", "message": f"Security risk: {p}", "failure_code": "E-SECURITY"})
    if "rule_applicator" not in main_content and "apply_rules" not in main_content: findings.append({"category": "LWP", "message": "LWP rule applicator missing", "failure_code": "E-LWP"})
    if "UI_MARKER" not in main_content and "spec_upload" not in main_content: findings.append({"category": "UI", "message": "Required UI markers missing", "failure_code": "E-UI"})
    if "Policy_Set" not in main_content or "Routing_Policy" not in main_content: findings.append({"category": "SCHEMA", "message": "ER Policy missing", "failure_code": "E-SCHEMA"})
    if len(findings) > 0: findings.append({"category": "FAILURE_CLASS", "message": f"{len(findings)} issues classified", "failure_code": "E-FAILURE_CLASS"})
    if "Entity" not in main_content or "Relationship" not in main_content: findings.append({"category": "ER_INTEGRITY", "message": "KU Entity/Relationship model incomplete", "failure_code": "E-ER_INTEGRITY"})
    passed = len(findings) == 0
    result = {"passed": passed, "findings": findings, "test_layers": 10}
    with open("reports/validation_default_run.json", "w", encoding="utf-8") as f: json.dump(result, f, indent=2)
    return result
