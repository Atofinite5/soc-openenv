"""FastAPI server for SOC Incident Response OpenEnv."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .environment import SocEnvironment
from .models import ResetRequest, SocAction, SocStepResult, EnvState

app = FastAPI(title="SOC Incident Response OpenEnv", version="1.0.0")
env = SocEnvironment()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset", response_model=SocStepResult)
def reset(req: ResetRequest | None = None):
    try:
        task_id = req.task_id if req else None
        return env.reset(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=SocStepResult)
def step(action: SocAction):
    try:
        return env.step(action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=EnvState)
def state():
    try:
        return env.get_state()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


def serve() -> None:
    """Entry point used by `[project.scripts]` to launch the server."""
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    serve()
