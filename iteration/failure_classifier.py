from typing import Dict, Any, List


class FailureClassifier:
    """
    Deterministic failure taxonomy for P6 validation.
    """

    TAXONOMY = {
        "SPEC_UNDERDETERMINED": "E-SPEC-UNDERDETERMINED",
        "SYNTAX": "E-SYNTAX",
        "DEPENDENCY": "E-DEPENDENCY",
        "STRUCTURE": "E-STRUCTURE",
        "BEHAVIOUR": "E-BEHAVIOUR",
        "SCHEMA": "E-SCHEMA",
        "GOVERNANCE": "E-GOVERNANCE",
        "SECURITY": "E-SECURITY",
        "LWP": "E-LWP",
        "UI": "E-UI",
        "RUNTIME": "E-RUNTIME",
        "UNKNOWN": "E-UNKNOWN",
    }

    def classify(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        classified = []
        for finding in findings:
            category = finding.get("category", "UNKNOWN")
            code = self.TAXONOMY.get(category, self.TAXONOMY["UNKNOWN"])
            enriched = dict(finding)
            enriched["failure_code"] = code
            classified.append(enriched)
        return classified
