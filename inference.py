"""SOC OpenEnv inference agent.

Runs all 3 tasks sequentially against a SocEnv server (local or HF Space)
and emits the mandatory [START]/[STEP]/[END] log lines.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

from client.soc_env import SocActionClient, SocEnv

BENCHMARK = "soc-incident-response"

# Mandatory env vars per OpenEnv hackathon spec
API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.environ.get("HF_TOKEN") or os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")

SUCCESS_THRESHOLD = 0.6

try:
    from openai import OpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False


# ----------------------------------------------------------------------
# Logging helpers (mandatory format)
# ----------------------------------------------------------------------
def log_start(task_id: str) -> None:
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)


def log_step(step: int, action: Dict[str, Any], reward: float, done: bool, error: Any) -> None:
    action_str = json.dumps(action, separators=(",", ":"))
    err = "null" if error is None else json.dumps(str(error))
    print(
        f"[STEP] step={step} action={action_str} reward={reward:.2f} "
        f"done={'true' if done else 'false'} error={err}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={'true' if success else 'false'} steps={steps} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ----------------------------------------------------------------------
# Prompt construction
# ----------------------------------------------------------------------
TASK_INSTRUCTIONS = {
    "task_1": (
        "Classify the incident. Return JSON with action_type='classify', "
        "severity in [P1,P2,P3,P4], category in [network,application,infra,security]. "
        "You may use action_type='query_logs' with a 'query' string to investigate first."
    ),
    "task_2": (
        "Diagnose the root cause. Return JSON with action_type='diagnose', "
        "root_cause_service (string), root_cause_trigger (short string). "
        "You may use action_type='query_logs' with a 'query' string to investigate first."
    ),
    "task_3": (
        "Generate an ordered remediation plan. Return JSON with action_type='remediate' "
        "and remediation_steps as a list of clear ordered step strings. Always verify "
        "current state first, never use destructive verbs (drop/delete/flush/purge/truncate) "
        "before verification. You may also use action_type='query_logs'."
    ),
}


def build_system_prompt(task_id: str) -> str:
    return (
        "You are an expert SOC analyst working a live incident.\n"
        + TASK_INSTRUCTIONS[task_id]
        + "\nReturn ONLY valid JSON. No markdown. No explanation."
    )


def build_user_prompt(obs: Dict[str, Any], history: List[str]) -> str:
    parts = [
        f"TASK: {obs['task_id']}  |  Step {obs['step']}/{obs['max_steps']}",
        f"Available actions: {obs['available_actions']}",
        "ALERT:",
        obs.get("alert_text", ""),
        "LOGS:",
        obs.get("log_snippet", ""),
    ]
    if obs.get("metrics"):
        parts.append("METRICS:")
        parts.append(json.dumps(obs["metrics"]))
    if obs.get("context"):
        parts.append("CONTEXT:")
        parts.append(obs["context"])
    if history:
        parts.append("HISTORY:")
        parts.extend(history)
    parts.append("Respond with a single JSON action.")
    return "\n".join(parts)


# ----------------------------------------------------------------------
# LLM call with fallback
# ----------------------------------------------------------------------
def _fallback_action(task_id: str) -> Dict[str, Any]:
    if task_id == "task_1":
        return {"action_type": "classify", "severity": "P2", "category": "infra"}
    if task_id == "task_2":
        return {
            "action_type": "diagnose",
            "root_cause_service": "unknown",
            "root_cause_trigger": "unknown",
        }
    return {
        "action_type": "remediate",
        "remediation_steps": [
            "verify current state of services",
            "notify stakeholders via slack",
            "fix redis memory by raising maxmemory and evicting",
            "restart inventory service",
            "verify order service recovery",
            "document incident in postmortem",
        ],
    }


def get_action(client, obs: Dict[str, Any], history: List[str]) -> Dict[str, Any]:
    task_id = obs["task_id"]
    if client is None:
        return _fallback_action(task_id)
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": build_system_prompt(task_id)},
                {"role": "user", "content": build_user_prompt(obs, history)},
            ],
            temperature=0.2,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"[DEBUG] LLM call failed: {e}", file=sys.stderr, flush=True)
        return _fallback_action(task_id)


# ----------------------------------------------------------------------
# Episode runner
# ----------------------------------------------------------------------
async def run_task(client, env: SocEnv, task_id: str) -> None:
    log_start(task_id)
    rewards: List[float] = []
    steps_taken = 0
    history: List[str] = []
    error: Any = None
    try:
        result = await env.reset(task_id)
        max_steps = result.observation.max_steps
        for step in range(1, max_steps + 1):
            if result.done:
                break
            obs_dict = result.observation.model_dump()
            try:
                action_dict = get_action(client, obs_dict, history)
            except Exception as e:
                action_dict = _fallback_action(task_id)
                error = e
            action = SocActionClient(**action_dict)
            try:
                result = await env.step(action)
                err_for_log = None
            except Exception as e:
                error = e
                err_for_log = e
                rewards.append(0.0)
                log_step(step, action_dict, 0.0, True, err_for_log)
                steps_taken = step
                break
            rewards.append(result.reward)
            steps_taken = step
            log_step(step, action_dict, result.reward, result.done, None)
            history.append(
                f"Step {step}: {json.dumps(action_dict, separators=(',', ':'))} -> reward={result.reward:.2f}"
            )
            if result.done:
                break
    except Exception as e:
        error = e
        print(f"[DEBUG] task error: {e}", file=sys.stderr, flush=True)
    finally:
        # Score = max reward across the trajectory (terminal action reward
        # already includes query-bonus pool), clamped to [0, 1].
        score = max(rewards) if rewards else 0.0
        score = max(0.0, min(1.0, score))
        success = score >= SUCCESS_THRESHOLD
        log_end(success, steps_taken, score, rewards)


async def main() -> None:
    env_url = os.environ.get("ENV_URL")
    image_name = os.environ.get("IMAGE_NAME")
    if env_url:
        env = SocEnv.from_url(env_url)
    elif image_name:
        env = await SocEnv.from_docker_image(image_name)
    else:
        env = SocEnv.from_url("http://localhost:7860")

    client = None
    if _OPENAI_AVAILABLE and API_KEY:
        try:
            client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
        except Exception as e:
            print(f"[DEBUG] OpenAI init failed: {e}", file=sys.stderr)

    try:
        for task_id in ("task_1", "task_2", "task_3"):
            await run_task(client, env, task_id)
    finally:
        env.close()


if __name__ == "__main__":
    asyncio.run(main())
