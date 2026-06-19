from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """Configures Cross-Origin Resource Sharing (CORS) middleware for the FastAPI app.
    Allows Next.js frontend running locally on port 3000 to interact with the API.
    """
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
