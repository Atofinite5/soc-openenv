"""Server package exposing the FastAPI app for openenv-core compliance."""
from .app import app, main

__all__ = ["app", "main"]
