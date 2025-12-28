"""FastAPI app exposing the estimator microservice."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
import logging
from typing import Any, Dict, Optional, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import AppConfig
from .events import Event, utc_now
from .service import EstimatorService
from .session_manager import SessionManager
from .session_api import (
    SessionAPI, SessionStartRequest, SessionEndRequest, 
    SessionUpdateRequest, CognitiveLogRequest, MilestoneRequest
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EventIn(BaseModel):
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class EmaResponseIn(BaseModel):
    prompt_id: int
    rating: int = Field(ge=1, le=7)
    disposition: str
    note: Optional[str] = None


class PrivacyToggle(BaseModel):
    active: bool


class ConsentToggle(BaseModel):
    granted: bool


class ExportRequest(BaseModel):
    reviewer: Optional[str] = None


class ExportApproval(BaseModel):
    reviewer: str
    token: Optional[str] = None


class ContextBlocklistUpdate(BaseModel):
    entries: List[str]


class IdleBlockUpdate(BaseModel):
    seconds: int = Field(ge=0, le=86400)

def create_service(config_path: Optional[Path] = None) -> EstimatorService:
    config = AppConfig.load(config_path)
    config.ensure_storage_parent()
    logger.info("Loaded app configuration (config_path=%s)", config_path or "default")
    return EstimatorService(config)


def create_session_manager(config_path: Optional[Path] = None) -> SessionManager:
    config = AppConfig.load(config_path)
    config.ensure_storage_parent()
    logger.info("Creating session manager with storage path=%s", config.session_tracking.storage_path)
    return SessionManager(config.session_tracking.storage_path)


def create_app(config_path: Optional[Path] = None) -> FastAPI:
    logger.info("Creating estimator service")
    service = create_service(config_path)
    session_manager = create_session_manager(config_path)
    session_api = SessionAPI(session_manager)
    
    app = FastAPI(title="Cognitive Load Estimator (Python)", version="0.1.0")
    app.state.service = service
    app.state.session_manager = session_manager
    app.state.session_api = session_api

    # Allow local Next.js dev server by default
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        logger.info("Starting estimator service runtime loop")
        await service.start()
        await session_manager.initialize()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        logger.info("Stopping estimator service runtime loop")
        await service.stop()
        await session_manager.close()

    def get_service() -> EstimatorService:
        return app.state.service

    def get_session_manager() -> SessionManager:
        return app.state.session_manager

    def get_session_api() -> SessionAPI:
        return app.state.session_api

    @app.post("/events")
    async def ingest_event(evt: EventIn, svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        logger.debug("Received event from %s with payload keys=%s", evt.source, list(evt.payload.keys()))
        event = Event(
            timestamp=evt.timestamp or utc_now(),
            source=evt.source,
            payload=evt.payload,
        )
        accepted = await svc.ingest_event(event)
        return {"accepted": accepted}

    @app.post("/ema/response")
    async def ema_response(
        payload: EmaResponseIn, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, Any]:
        logger.info(
            "Recording EMA response (prompt_id=%s disposition=%s)",
            payload.prompt_id,
            payload.disposition,
        )
        await svc.ingest_ema_response(
            prompt_id=payload.prompt_id,
            rating=payload.rating,
            disposition=payload.disposition,
            note=payload.note,
        )
        return {"status": "ok"}

    @app.get("/estimate")
    async def latest_estimate(svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        payload = svc.latest_payload()
        if not payload:
            raise HTTPException(status_code=404, detail="no estimate yet")
        return payload

    @app.get("/health")
    async def health(svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        state = svc.latest()
        return {
            "status": "ok",
            "baseline_active": state.baseline_active if state else True,
            "hop_index": state.hop_index if state else 0,
        }

    @app.get("/telemetry")
    async def telemetry(svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        return svc.telemetry()

    @app.get("/ema/pending")
    async def pending_prompt(svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        prompt = await svc.pending_prompt()
        return {"prompt": prompt}

    @app.get("/telemetry/feed")
    async def telemetry_feed(
        limit: int = 200, svc: EstimatorService = Depends(get_service)
    ) -> StreamingResponse:
        async def iterator():
            metrics = await svc.storage.fetch_telemetry_metrics(limit)
            for metric in metrics:
                yield json.dumps(metric) + "\n"

        return StreamingResponse(iterator(), media_type="application/x-ndjson")

    @app.get("/stream/state")
    async def stream_state(svc: EstimatorService = Depends(get_service)) -> StreamingResponse:
        async def event_generator():
            try:
                async for snapshot in svc.state_updates():
                    yield f"data: {json.dumps(snapshot, default=str)}\n\n"
            except asyncio.CancelledError:
                return

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/privacy")
    async def set_privacy(
        payload: PrivacyToggle, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, bool]:
        logger.info("Privacy pause set to %s", payload.active)
        svc.set_privacy_pause(payload.active)
        return svc.permissions_status()

    @app.post("/consent")
    async def set_consent(
        payload: ConsentToggle, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, bool]:
        logger.info("Consent flag set to %s", payload.granted)
        svc.set_consent(payload.granted)
        return svc.permissions_status()

    @app.get("/permissions")
    async def permissions(svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        logger.debug("Permissions status requested")
        return svc.permissions_status()

    @app.post("/permissions/context")
    async def update_context_blocklist(
        payload: ContextBlocklistUpdate, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, Any]:
        logger.info("Updating context blocklist to %s", payload.entries)
        svc.set_context_blocklist(payload.entries)
        return svc.permissions_status()

    @app.post("/permissions/idle")
    async def update_idle_block(
        payload: IdleBlockUpdate, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, Any]:
        logger.info("Updating idle block seconds to %s", payload.seconds)
        svc.set_idle_block_seconds(payload.seconds)
        return svc.permissions_status()

    @app.get("/policy/consent")
    async def consent_history(svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        return {"entries": svc.consent_history()}

    @app.get("/policy/events")
    async def policy_events(
        limit: int = 100, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, Any]:
        return {"events": await svc.policy_events(limit)}

    @app.post("/export/request")
    async def export_request(
        payload: ExportRequest, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, Any]:
        try:
            result = await svc.request_export(payload.reviewer)
        except RuntimeError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        return result

    @app.get("/export")
    async def list_exports(status: Optional[str] = None, svc: EstimatorService = Depends(get_service)) -> Dict[str, Any]:
        exports = await svc.list_exports(status)
        return {"exports": exports}

    @app.post("/export/{export_id}/approve")
    async def approve_export(
        export_id: int, payload: ExportApproval, svc: EstimatorService = Depends(get_service)
    ) -> Dict[str, Any]:
        try:
            export = await svc.approve_export(export_id, payload.reviewer, payload.token)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        except (RuntimeError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return export

    @app.get("/export/{export_id}/download")
    async def download_export(export_id: int, svc: EstimatorService = Depends(get_service)) -> FileResponse:
        export = await svc.get_export(export_id)
        if not export or export["status"] != "approved" or not export.get("file_path"):
            raise HTTPException(status_code=404, detail="approved export not found")
        path = Path(export["file_path"])
        if not path.exists():
            raise HTTPException(status_code=404, detail="export file missing")
        return FileResponse(path, filename=path.name, media_type="application/json")

    # Session tracking endpoints
    @app.post("/sessions/start")
    async def start_session(
        request: SessionStartRequest, api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.start_session(request)

    @app.post("/sessions/end")
    async def end_session(
        request: SessionEndRequest, api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.end_session(request)

    @app.get("/sessions/current")
    async def get_current_session(api: SessionAPI = Depends(get_session_api)) -> Dict[str, Any]:
        return await api.get_current_session()

    @app.get("/sessions/status")
    async def get_session_status(api: SessionAPI = Depends(get_session_api)) -> Dict[str, Any]:
        return await api.get_session_status()

    @app.get("/sessions/{session_uuid}")
    async def get_session_summary(
        session_uuid: str, api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.get_session_summary(session_uuid)

    @app.get("/sessions")
    async def list_sessions(
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.list_sessions(limit, start_date, end_date)

    @app.put("/sessions/{session_uuid}")
    async def update_session(
        session_uuid: str,
        request: SessionUpdateRequest,
        api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.update_session(session_uuid, request)

    @app.delete("/sessions/{session_uuid}")
    async def delete_session(
        session_uuid: str, api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.delete_session(session_uuid)

    @app.post("/sessions/log-cognitive-load")
    async def log_cognitive_load(
        request: CognitiveLogRequest, api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.log_cognitive_load(request)

    @app.post("/sessions/milestones")
    async def add_milestone(
        request: MilestoneRequest, api: SessionAPI = Depends(get_session_api)
    ) -> Dict[str, Any]:
        return await api.add_milestone(request)

    return app
