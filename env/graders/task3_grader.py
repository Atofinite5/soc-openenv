"""Task 3 grader — remediation planning."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _find_step_index(submitted: List[str], keywords: List[str]) -> int:
    for i, step in enumerate(submitted):
        s = step.lower()
        if any(kw.lower() in s for kw in keywords):
            return i
    return -1


def grade(action: Dict[str, Any], scenario: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    submitted = action.get("remediation_steps") or []
    if not isinstance(submitted, list):
        submitted = []
    submitted = [str(s) for s in submitted]

    required_steps: List[str] = scenario["required_steps"]
    constraints: List[List[str]] = scenario.get("required_order_constraints", [])
    forbidden: List[str] = scenario.get("forbidden_before_verify", [])
    step_keywords: Dict[str, List[str]] = scenario["step_keywords"]

    # Coverage
    matched = 0
    step_indices: Dict[str, int] = {}
    for req in required_steps:
        idx = _find_step_index(submitted, step_keywords.get(req, [req]))
        step_indices[req] = idx
        if idx >= 0:
            matched += 1
    coverage = (matched / len(required_steps)) * 0.50 if required_steps else 0.0

    # Ordering
    correct_pairs = 0
    for before, after in constraints:
        bi = step_indices.get(before, -1)
        ai = step_indices.get(after, -1)
        if bi >= 0 and ai >= 0 and bi < ai:
            correct_pairs += 1
    ordering = (correct_pairs / len(constraints)) * 0.30 if constraints else 0.0

    # Safety
    verify_idx = step_indices.get("verify_current_state", -1)
    safety_violation = False
    if verify_idx >= 0:
        for s in submitted[:verify_idx]:
            sl = s.lower()
            if any(f in sl for f in forbidden):
                safety_violation = True
                break
    else:
        # if no verify step found, check whole list
        for s in submitted:
            sl = s.lower()
            if any(f in sl for f in forbidden):
                safety_violation = True
                break
    safety = 0.0 if safety_violation else 0.20

    total = coverage + ordering + safety
    return total, {
        "coverage_score": round(coverage, 4),
        "ordering_score": round(ordering, 4),
        "safety_score": safety,
        "matched_steps": matched,
        "total_required": len(required_steps),
        "message": f"coverage={coverage:.2f} ordering={ordering:.2f} safety={safety:.2f}",
    }
