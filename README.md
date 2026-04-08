---
title: SOC Incident Response OpenEnv
emoji: 🛡️
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
tags:
  - openenv
  - security
  - incident-response
---

# SOC Incident Response — OpenEnv

A containerised OpenEnv-compatible training environment where an agent plays a Level-1/2 SOC analyst across three tasks of increasing difficulty.

## Tasks

| ID | Name | Difficulty | Max Steps | Terminal Action |
|----|------|------------|-----------|-----------------|
| task_1 | Incident Classification | easy | 5 | classify |
| task_2 | Root Cause Diagnosis | medium | 8 | diagnose |
| task_3 | Remediation Planning | hard | 12 | remediate |

All graders are deterministic — no LLM calls inside the environment.

## Action Space

```json
{
  "action_type": "classify | query_logs | diagnose | remediate",
  "severity": "P1 | P2 | P3 | P4",
  "category": "network | application | infra | security",
  "query": "string",
  "root_cause_service": "string",
  "root_cause_trigger": "string",
  "remediation_steps": ["step 1", "step 2"]
}
```

## Observation Space

```json
{
  "task_id": "task_1",
  "step": 0,
  "max_steps": 5,
  "alert_text": "...",
  "log_snippet": "...",
  "metrics": {},
  "available_actions": ["classify", "query_logs"],
  "context": null
}
```

## Endpoints

| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | /reset | `{}` or `{"task_id":"task_1"}` | Empty body OK |
| POST | /step  | SocAction JSON | `action_type` required |
| GET  | /state | — | Debug |
| GET  | /health | — | Validator ping |

## Run locally

```bash
pip install -r requirements.txt
uvicorn env.main:app --host 0.0.0.0 --port 7860
ENV_URL=http://localhost:7860 python inference.py
```

## Run via Docker

```bash
docker build -t soc-openenv .
docker run -p 7860:7860 soc-openenv
IMAGE_NAME=soc-openenv python inference.py
```

## Baseline scores (Qwen2.5-72B-Instruct)

| Task | Expected |
|------|----------|
| task_1 | 0.55 – 0.75 |
| task_2 | 0.30 – 0.60 |
| task_3 | 0.25 – 0.50 |
