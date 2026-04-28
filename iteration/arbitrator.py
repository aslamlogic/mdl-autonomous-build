from typing import Dict, Any
def arbitrate(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    if primary.get("passed") and not secondary.get("passed"): return {"status": "ARBITRATED", "winner": "primary", "result": primary}
    if not primary.get("passed") and secondary.get("passed"): return {"status": "ARBITRATED", "winner": "secondary", "result": secondary}
    return {"status": "CONFLICT", "primary": primary, "secondary": secondary}
