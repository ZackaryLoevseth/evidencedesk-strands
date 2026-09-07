from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .agent import model_status, run_case
from .core import CaseInput, ReviewInput, create_case, export_packet
from .sources import fetch_source
from .store import Store

ROOT = Path(__file__).parent


class FetchInput(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="EvidenceDesk", docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])
    store = Store(data_dir or os.environ.get("EVIDENCEDESK_DATA", ".data/cases"))
    store.recover()
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="evidencedesk")
    run_lock = threading.Lock()
    app.state.store = store

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method in {"POST", "PUT", "DELETE", "PATCH"} and origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Use the local EvidenceDesk page for changes."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static/index.html")

    @app.get("/api/status")
    def status():
        return {**model_status(), "busy": run_lock.locked()}

    @app.get("/api/sample")
    def sample():
        return json.loads((ROOT / "fixtures/source_pack.json").read_text())

    @app.get("/api/cases")
    def list_cases():
        return store.list()

    @app.post("/api/cases", status_code=201)
    def new_case(data: CaseInput):
        return store.save(create_case(data))

    def get_case(case_id):
        try:
            return store.get(case_id)
        except KeyError:
            raise HTTPException(404, "Case not found.") from None

    @app.get("/api/cases/{case_id}")
    def read_case(case_id: str):
        return get_case(case_id)

    @app.post("/api/cases/{case_id}/run", status_code=202)
    def start_run(case_id: str):
        case = get_case(case_id)
        if case["status"] != "ready":
            raise HTTPException(409, "A case can run once. Duplicate the inputs to preserve this run and start another.")
        status = model_status()
        if not status["available"]:
            raise HTTPException(503, status["reason"])
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, "One local model run is already active. Please wait.")
        case["status"] = "queued"
        store.save(case)

        def work():
            try:
                run_case(case, store.save)
            except Exception as exc:
                case["status"] = "failed"
                case["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
                store.save(case)
            finally:
                run_lock.release()

        pool.submit(work)
        return {"id": case_id, "status": "queued"}

    @app.post("/api/cases/{case_id}/review")
    def review(case_id: str, data: ReviewInput):
        get_case(case_id)
        try:
            return store.review(case_id, data.model_dump())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.get("/api/cases/{case_id}/packet.zip")
    def packet(case_id: str):
        case = get_case(case_id)
        if case["status"] in {"queued", "running"}:
            raise HTTPException(409, "Wait for the run to finish before exporting.")
        return Response(export_packet(case), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="evidencedesk-{case_id}.zip"'})

    @app.post("/api/fetch")
    def fetch(data: FetchInput):
        try:
            return fetch_source(data.url)
        except (ValueError, httpx.HTTPError) as exc:
            raise HTTPException(400, str(exc)) from None

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    return app
