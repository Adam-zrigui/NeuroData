"""Small FastAPI service used by a future thin demo client."""

import os
import threading
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import connect
from parse_query import Filters, parse_query
from search_core import search

app = FastAPI(
    title="NeuroData Finder",
    version="0.1.0",
    description=(
        "Search public OpenNeuro MRI/fMRI metadata. Results are suggestions; read the dataset's "
        "own documentation before relying on a match."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_rate_lock = threading.Lock()
_last_search_time = 0.0


@app.middleware("http")
async def limit_search_rate(request: Request, call_next):
    """Apply a small global throttle without persisting IPs or query contents."""
    global _last_search_time
    if request.url.path in {"/search", "/parse"}:
        with _rate_lock:
            now = time.monotonic()
            if now - _last_search_time < 0.1:
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=429, content={"detail": "Please slow down and retry."})
            _last_search_time = now
    return await call_next(request)


class SearchBody(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    filters: Filters | None = None
    limit: int = Field(default=10, ge=1, le=50)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    try:
        with connect() as conn:
            count = conn.execute("SELECT count(*) FROM datasets").fetchone()[0]
        return {"indexed_datasets": count}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@app.post("/parse")
def parse(body: SearchBody):
    return parse_query(body.query).model_dump()


@app.post("/search")
def search_endpoint(body: SearchBody):
    parsed = parse_query(body.query)
    filters = body.filters or parsed.filters
    try:
        return {
            "query": body.query,
            "parsed": {"semantic_query": parsed.semantic_query, "filters": filters.model_dump()},
            "results": search(parsed.semantic_query, filters, body.limit),
            "notice": "Matches are suggestions; review original dataset documentation before relying on them.",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Search service unavailable") from exc
