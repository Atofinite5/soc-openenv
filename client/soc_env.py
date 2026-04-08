"""Async HTTP client wrapper for SOC OpenEnv."""
from __future__ import annotations

import asyncio
import subprocess
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field


class SocObservationClient(BaseModel):
    task_id: str
    step: int
    max_steps: int
    alert_text: str
    log_snippet: str
    metrics: Optional[Dict[str, Any]] = None
    available_actions: List[str]
    context: Optional[str] = None


class SocActionClient(BaseModel):
    action_type: str
    severity: Optional[str] = None
    category: Optional[str] = None
    query: Optional[str] = None
    service_name: Optional[str] = None
    root_cause_service: Optional[str] = None
    root_cause_trigger: Optional[str] = None
    remediation_steps: Optional[List[str]] = None


class SocEnvResult(BaseModel):
    observation: SocObservationClient
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class SocEnv:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._container_id: Optional[str] = None

    # ------------------------------------------------------------------
    @classmethod
    def from_url(cls, url: str) -> "SocEnv":
        return cls(url)

    @classmethod
    async def from_docker_image(
        cls, image_name: str, port: int = 7860, timeout: int = 45
    ) -> "SocEnv":
        result = subprocess.run(
            ["docker", "run", "-d", "-p", f"{port}:7860", image_name],
            check=True,
            capture_output=True,
            text=True,
        )
        container_id = result.stdout.strip()
        env = cls(f"http://localhost:{port}")
        env._container_id = container_id
        await env._wait_for_health(timeout)
        return env

    # ------------------------------------------------------------------
    async def _wait_for_health(self, timeout: int) -> None:
        deadline = asyncio.get_event_loop().time() + timeout
        async with aiohttp.ClientSession() as session:
            while asyncio.get_event_loop().time() < deadline:
                try:
                    async with session.get(f"{self.base_url}/health", timeout=2) as r:
                        if r.status == 200:
                            return
                except Exception:
                    pass
                await asyncio.sleep(1)
        raise TimeoutError(f"Env not healthy after {timeout}s")

    async def _post(self, path: str, payload: Dict[str, Any]) -> SocEnvResult:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}{path}", json=payload, timeout=30) as r:
                data = await r.json()
                if r.status >= 400:
                    raise RuntimeError(f"{path} failed [{r.status}]: {data}")
                return SocEnvResult(**data)

    # ------------------------------------------------------------------
    async def reset(self, task_id: str = "task_1") -> SocEnvResult:
        return await self._post("/reset", {"task_id": task_id})

    async def step(self, action: SocActionClient) -> SocEnvResult:
        return await self._post("/step", action.model_dump(exclude_none=True))

    def close(self) -> None:
        if self._container_id:
            subprocess.run(["docker", "stop", self._container_id], capture_output=True)
            subprocess.run(["docker", "rm", self._container_id], capture_output=True)
            self._container_id = None
