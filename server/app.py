"""OpenEnv-core entrypoint.

This module re-exports the FastAPI `app` from `env.main` so that tooling
that follows the openenv-core convention of looking up `server.app:app`
(or `server/app.py`) can discover and launch the SOC environment server.
"""
from __future__ import annotations

import os

import uvicorn

from env.main import app

__all__ = ["app", "main"]


def main() -> None:
    """Entry point used by `[project.scripts]` to launch the server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
