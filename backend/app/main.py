"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.claims import router as claims_router
from app.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Plum Claims Processing System",
    description="Multi-agent health insurance claims processing pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
_wildcard = _origins_env.strip() == "*"
_allowed_origins = ["*"] if _wildcard else [o.strip() for o in _origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=not _wildcard,  # credentials + wildcard is invalid per CORS spec
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims_router, prefix="/api")
