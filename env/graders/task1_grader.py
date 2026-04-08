"""Task 1 grader — incident classification."""
from __future__ import annotations

from typing import Any, Dict, Tuple

SEV_ORDER = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


def grade(action: Dict[str, Any], scenario: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    sev = action.get("severity")
    cat = action.get("category")
    correct_sev = scenario["correct_severity"]
    correct_cat = scenario["correct_category"]

    if sev == correct_sev:
        sev_score = 0.50
        sev_msg = f"Severity correct (+0.50)"
    elif sev in SEV_ORDER and abs(SEV_ORDER[sev] - SEV_ORDER[correct_sev]) == 1:
        sev_score = 0.25
        sev_msg = f"Severity one level off (+0.25)"
    else:
        sev_score = 0.0
        sev_msg = "Severity wrong"

    if cat == correct_cat:
        cat_score = 0.50
        cat_msg = "Category correct (+0.50)"
    else:
        cat_score = 0.0
        cat_msg = "Category wrong"

    total = sev_score + cat_score
    return total, {
        "severity_score": sev_score,
        "category_score": cat_score,
        "message": f"{sev_msg} | {cat_msg}",
    }


def grade_query_logs(query: str, scenario: Dict[str, Any]) -> float:
    if not query:
        return 0.0
    q = query.lower()
    keywords = scenario.get("query_keywords", [])
    matches = sum(1 for kw in keywords if kw.lower() in q)
    if matches == 0:
        return 0.0
    return min(0.05, 0.05 * matches)
