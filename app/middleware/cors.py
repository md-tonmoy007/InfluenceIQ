from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """Configures Cross-Origin Resource Sharing (CORS) middleware for the FastAPI app.

    Allowed origins:
    * ``localhost:3000`` / ``127.0.0.1:3000`` — Next.js dev server (host port 3000)
    * ``localhost:3002`` / ``127.0.0.1:3002`` — Next.js containerised (host port 3002)
    * ``localhost:8000`` / ``localhost:8002`` — backend-core itself (for health/probes)
    """
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:8000",
        "http://localhost:8002",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
