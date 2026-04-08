"""OpenEnv-core entrypoint.

This module re-exports the FastAPI `app` from `env.main` so that tooling
that follows the openenv-core convention of looking up `server.app:app`
(or `server/app.py`) can discover and launch the SOC environment server.
"""
from __future__ import annotations

from env.main import app, serve

__all__ = ["app", "serve"]


if __name__ == "__main__":
    serve()
