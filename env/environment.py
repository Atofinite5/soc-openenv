"""SOC Incident Response environment state machine."""
from __future__ import annotations

import json
import math
import os
import random
from typing import Any, Dict, Optional

from .models import EnvState, SocAction, SocObservation, SocStepResult
from .graders import task1_grader, task2_grader, task3_grader

SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")

TASK_CONFIG: Dict[str, Dict[str, Any]] = {
    "task_1": {
        "max_steps": 5,
        "grader": task1_grader,
        "available_actions": ["classify", "query_logs"],
        "terminal_action": "classify",
        "scenario_file": "task1_easy.json",
    },
    "task_2": {
        "max_steps": 8,
        "grader": task2_grader,
        "available_actions": ["diagnose", "query_logs"],
        "terminal_action": "diagnose",
        "scenario_file": "task2_medium.json",
    },
    "task_3": {
        "max_steps": 12,
        "grader": task3_grader,
        "available_actions": ["remediate", "query_logs"],
        "terminal_action": "remediate",
        "scenario_file": "task3_hard.json",
    },
}


def _load_scenarios(filename: str):
    path = os.path.join(SCENARIOS_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


class SocEnvironment:
    def __init__(self) -> None:
        self.state: Optional[EnvState] = None
        self.scenario: Optional[Dict[str, Any]] = None
        self.task_config: Optional[Dict[str, Any]] = None
        self.query_bonus_pool: float = 0.0

    # ------------------------------------------------------------------
    def reset(self, task_id: Optional[str] = None) -> SocStepResult:
        task_id = task_id or "task_1"
        if task_id not in TASK_CONFIG:
            raise ValueError(
                f"Unknown task_id '{task_id}'. Valid: {list(TASK_CONFIG.keys())}"
            )
        cfg = TASK_CONFIG[task_id]
        scenarios = _load_scenarios(cfg["scenario_file"])
        scenario = random.choice(scenarios)

        self.task_config = cfg
        self.scenario = scenario
        self.query_bonus_pool = 0.0
        self.state = EnvState(
            task_id=task_id,
            scenario_id=scenario["scenario_id"],
            step=0,
            max_steps=cfg["max_steps"],
            done=False,
            cumulative_reward=0.0,
            history=[],
        )
        return SocStepResult(
            observation=self._build_obs(),
            reward=0.0,
            done=False,
            info={"scenario_id": scenario["scenario_id"]},
        )

    # ------------------------------------------------------------------
    def step(self, action: SocAction) -> SocStepResult:
        if self.state is None:
            raise RuntimeError("Environment not initialised. Call reset() first.")
        if self.state.done:
            raise RuntimeError("Episode is done. Call reset() to start a new one.")

        self.state.step += 1
        cfg = self.task_config
        grader = cfg["grader"]
        terminal = cfg["terminal_action"]
        action_dict = action.model_dump(mode="json", exclude_none=False)
        # Convert enums to plain strings
        for k, v in list(action_dict.items()):
            if hasattr(v, "value"):
                action_dict[k] = v.value

        atype = action_dict.get("action_type")
        info: Dict[str, Any] = {"scenario_id": self.scenario["scenario_id"]}
        reward = 0.0
        done = False

        if atype == "query_logs":
            if hasattr(grader, "grade_query_logs"):
                q = action_dict.get("query") or ""
                r = grader.grade_query_logs(q, self.scenario)
                self.query_bonus_pool = min(0.15, self.query_bonus_pool + r)
                reward = r
                info["breakdown"] = {
                    "query_bonus_added": r,
                    "query_bonus_pool": self.query_bonus_pool,
                    "message": f"query_logs +{r:.2f}",
                }
            else:
                info["breakdown"] = {"message": "query_logs not supported"}
        elif atype == terminal:
            base, breakdown = grader.grade(action_dict, self.scenario)
            total = min(1.0, base + self.query_bonus_pool)
            reward = total
            done = True
            breakdown["base_score"] = round(base, 4)
            breakdown["query_bonus"] = round(self.query_bonus_pool, 4)
            info["breakdown"] = breakdown
        else:
            info["breakdown"] = {
                "message": f"action_type '{atype}' not valid for {self.state.task_id}",
            }
            reward = 0.0

        # Step penalty
        threshold = math.floor(self.state.max_steps * 0.8)
        if self.state.step > threshold:
            penalty = -0.02 * (self.state.step - threshold)
            reward = max(0.0, reward + penalty)
            info["breakdown"]["step_penalty"] = penalty

        if self.state.step >= self.state.max_steps:
            done = True

        self.state.cumulative_reward += reward
        self.state.done = done
        self.state.history.append(
            {"step": self.state.step, "action_type": atype, "reward": round(reward, 4)}
        )

        return SocStepResult(
            observation=self._build_obs(),
            reward=reward,
            done=done,
            info=info,
        )

    # ------------------------------------------------------------------
    def get_state(self) -> EnvState:
        if self.state is None:
            raise RuntimeError("Environment not initialised.")
        return self.state

    # ------------------------------------------------------------------
    def _build_obs(self) -> SocObservation:
        s = self.scenario
        tid = self.state.task_id
        if tid == "task_2":
            log_snippet = "\n---\n".join(
                f"[{svc}]\n" + "\n".join(data["logs"][:2])
                for svc, data in s["services"].items()
            )
            metrics = {svc: data["metrics"] for svc, data in s["services"].items()}
        else:
            log_snippet = s.get("log_snippet", "")
            metrics = s.get("metrics")
        return SocObservation(
            task_id=tid,
            step=self.state.step,
            max_steps=self.state.max_steps,
            alert_text=s["alert_text"],
            log_snippet=log_snippet,
            metrics=metrics,
            available_actions=self.task_config["available_actions"],
            context=s.get("full_context"),
        )
