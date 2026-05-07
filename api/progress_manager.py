"""
VEDA — Progress Manager
Manages WebSocket connections and broadcasts live agent progress events.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List
from fastapi import WebSocket


class ProgressManager:

    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.connections:
            self.connections[job_id] = []
        self.connections[job_id].append(websocket)
        print(f"[WS] Client connected to job {job_id}")

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.connections:
            if websocket in self.connections[job_id]:
                self.connections[job_id].remove(websocket)
            if not self.connections[job_id]:
                del self.connections[job_id]
        print(f"[WS] Client disconnected from job {job_id}")

    async def broadcast(self, job_id: str, event: dict):
        """Send a progress event to all clients watching this job."""
        event["timestamp"] = datetime.utcnow().isoformat()
        event["job_id"] = job_id
        message = json.dumps(event)

        if job_id not in self.connections:
            return

        dead = []
        for ws in self.connections[job_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections[job_id].remove(ws)

    # ── Convenience methods called by agents ──────────────────────────

    async def agent_started(self, job_id: str, step: int, agent_name: str, message: str):
        await self.broadcast(job_id, {
            "step":         step,
            "total_steps":  4,
            "agent":        agent_name,
            "status":       "RUNNING",
            "message":      message,
            "data":         {},
            "progress_pct": int((step - 1) / 4 * 100),
        })

    async def agent_completed(self, job_id: str, step: int, agent_name: str, message: str, data: dict = None):
        await self.broadcast(job_id, {
            "step":         step,
            "total_steps":  4,
            "agent":        agent_name,
            "status":       "DONE",
            "message":      message,
            "data":         data or {},
            "progress_pct": int(step / 4 * 100),
        })

    async def agent_failed(self, job_id: str, step: int, agent_name: str, error: str):
        await self.broadcast(job_id, {
            "step":         step,
            "total_steps":  4,
            "agent":        agent_name,
            "status":       "FAILED",
            "message":      f"Agent failed: {error}",
            "data":         {},
            "progress_pct": int((step - 1) / 4 * 100),
        })

    async def audit_completed(self, job_id: str, summary: dict):
        await self.broadcast(job_id, {
            "step":         4,
            "total_steps":  4,
            "agent":        "VEDA",
            "status":       "COMPLETED",
            "message":      "✅ VEDA audit complete. Full report ready.",
            "data":         summary,
            "progress_pct": 100,
        })

    async def audit_failed(self, job_id: str, error: str):
        await self.broadcast(job_id, {
            "step":         0,
            "total_steps":  4,
            "agent":        "VEDA",
            "status":       "FAILED",
            "message":      f"❌ Audit failed: {error}",
            "data":         {},
            "progress_pct": 0,
        })