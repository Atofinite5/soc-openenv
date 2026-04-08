"""Pydantic models for SOC Incident Response OpenEnv."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentCategory(str, Enum):
    NETWORK = "network"
    APPLICATION = "application"
    INFRA = "infra"
    SECURITY = "security"


class ActionType(str, Enum):
    CLASSIFY = "classify"
    QUERY_LOGS = "query_logs"
    DIAGNOSE = "diagnose"
    REMEDIATE = "remediate"


class SocObservation(BaseModel):
    task_id: str
    step: int
    max_steps: int
    alert_text: str
    log_snippet: str
    metrics: Optional[Dict[str, Any]] = None
    available_actions: List[str]
    context: Optional[str] = None


class SocAction(BaseModel):
    action_type: ActionType
    severity: Optional[Severity] = None
    category: Optional[IncidentCategory] = None
    query: Optional[str] = None
    service_name: Optional[str] = None
    root_cause_service: Optional[str] = None
    root_cause_trigger: Optional[str] = None
    remediation_steps: Optional[List[str]] = None


class SocStepResult(BaseModel):
    observation: SocObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class EnvState(BaseModel):
    task_id: str
    scenario_id: str
    step: int
    max_steps: int
    done: bool
    cumulative_reward: float
    history: List[Dict[str, Any]] = Field(default_factory=list)


class ResetRequest(BaseModel):
    task_id: Optional[str] = None
