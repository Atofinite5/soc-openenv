"""Task 2 grader — root cause diagnosis."""
from __future__ import annotations

from typing import Any, Dict, Tuple


def grade(action: Dict[str, Any], scenario: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    rcs = (action.get("root_cause_service") or "").lower().strip()
    trig = (action.get("root_cause_trigger") or "").lower().strip()
    correct_service = scenario["correct_root_cause_service"].lower()
    acceptable_triggers = [t.lower() for t in scenario.get("acceptable_triggers", [])]

    if rcs == correct_service:
        svc_score = 0.60
        svc_msg = "Service correct (+0.60)"
    elif rcs and (rcs in correct_service or correct_service in rcs or
                  any(part in rcs for part in correct_service.split("-") if len(part) > 3)):
        svc_score = 0.30
        svc_msg = "Service partial (+0.30)"
    else:
        svc_score = 0.0
        svc_msg = "Service wrong"

    if any(at in trig for at in acceptable_triggers):
        trig_score = 0.40
        trig_msg = "Trigger correct (+0.40)"
    else:
        trig_score = 0.0
        trig_msg = "Trigger wrong"

    total = svc_score + trig_score
    return total, {
        "service_score": svc_score,
        "trigger_score": trig_score,
        "message": f"{svc_msg} | {trig_msg}",
    }


def grade_query_logs(query: str, scenario: Dict[str, Any]) -> float:
    if not query:
        return 0.0
    q = query.lower()
    kw_by_svc = scenario.get("query_keywords_by_service", {})
    for svc, kws in kw_by_svc.items():
        if any(kw.lower() in q for kw in kws):
            return 0.05
    return 0.0
