"""
FastAPI backend for the AI Airport Support Agent.

Wraps the same agent.py / data.py logic used in the Streamlit version,
exposed as a REST API so a real React frontend can talk to it.

Run with:
    uvicorn main:app --reload --port 8000
"""

import uuid
import json
import asyncio

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data import BOOKINGS, FLIGHTS
from agent import (
    run_pipeline,
    create_refund_request,
    confirm_rebooking,
    escalate_to_human,
)
from database import get_db
from models import AuditLog
from disruption_engine import run_disruption_simulation

app = FastAPI(title="Airport Support Agent API")

# Allow the Vite dev server (and any local frontend) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# WebSockets Connection Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# in-memory store for pending decisions, keyed by a request id
PENDING: dict[str, dict] = {}

class QueryRequest(BaseModel):
    text: str
    pnr: str


@app.get("/api/bookings")
def list_bookings():
    return list(BOOKINGS.values())


@app.get("/api/bookings/{pnr}")
def get_booking(pnr: str):
    booking = BOOKINGS.get(pnr)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


@app.post("/api/query")
async def submit_query(req: QueryRequest, db: Session = Depends(get_db)):
    if req.pnr not in BOOKINGS:
        raise HTTPException(404, "Unknown PNR")

    result = run_pipeline(req.text, req.pnr)
    request_id = str(uuid.uuid4())

    booking = BOOKINGS[req.pnr]
    flight = FLIGHTS.get(booking["flight_no"])

    PENDING[request_id] = {
        "query_type": result["query_type"],
        "decision": result["decision"],
        "pnr": req.pnr,
        "text": req.text,
    }

    # If it's auto-resolved, log it to the audit DB
    if result["route"] == "auto":
        log_entry = AuditLog(
            request_id=request_id,
            pnr=req.pnr,
            action_type="auto-execute",
            ai_decision=json.dumps(result["decision"]),
            human_approver=None,
            outcome="Auto-resolved by Agent"
        )
        db.add(log_entry)
        db.commit()

    response_data = {
        "request_id": request_id,
        "query_type": result["query_type"],
        "citation": result["citation"],
        "citation_text": result["citation_text"],
        "decision": result["decision"],
        "route": result["route"],
        "log": [{"step": s, "detail": d} for s, d in result["log"]],
        "booking": booking,
        "flight": flight,
    }
    
    # Broadcast new query to the ops dashboard
    await manager.broadcast({"type": "NEW_QUERY", "data": response_data})

    return response_data


@app.post("/api/approve/{request_id}")
async def approve(request_id: str, db: Session = Depends(get_db)):
    pending = PENDING.get(request_id)
    if not pending:
        raise HTTPException(404, "No pending decision for this request")

    qtype = pending["query_type"]
    decision = pending["decision"]
    pnr = pending["pnr"]

    if qtype == "cancellation":
        outcome = create_refund_request(pnr, decision.get("refund_amount", 0))
    elif qtype == "rebooking":
        options = decision.get("options", [])
        if not options:
            raise HTTPException(400, "No rebooking options available")
        outcome = confirm_rebooking(pnr, options[0]["flight_no"])
    else:
        raise HTTPException(400, f"Query type '{qtype}' is not approval-executable")

    # Log to Audit Database
    log_entry = AuditLog(
        request_id=request_id,
        pnr=pnr,
        action_type="approve",
        ai_decision=json.dumps(decision),
        human_approver="OpsAgent1", # In a real app, this comes from auth
        outcome=json.dumps(outcome)
    )
    db.add(log_entry)
    db.commit()

    del PENDING[request_id]
    
    await manager.broadcast({"type": "STATUS_UPDATE", "request_id": request_id, "status": "approved"})
    return {"status": "executed", "outcome": outcome}


@app.post("/api/escalate/{request_id}")
async def escalate(request_id: str, db: Session = Depends(get_db)):
    pending = PENDING.get(request_id)
    if not pending:
        raise HTTPException(404, "No pending decision for this request")

    reason = pending["decision"].get("reasoning", "Escalated by user choice")
    outcome = escalate_to_human(reason)
    pnr = pending["pnr"]
    
    # Log to Audit Database
    log_entry = AuditLog(
        request_id=request_id,
        pnr=pnr,
        action_type="escalate",
        ai_decision=json.dumps(pending["decision"]),
        human_approver="OpsAgent1",
        outcome=json.dumps(outcome)
    )
    db.add(log_entry)
    db.commit()

    del PENDING[request_id]
    
    await manager.broadcast({"type": "STATUS_UPDATE", "request_id": request_id, "status": "escalated"})
    return outcome


@app.post("/api/simulate_disruption")
async def trigger_disruption(background_tasks: BackgroundTasks):
    """Triggers the proactive disruption engine."""
    background_tasks.add_task(run_disruption_simulation, manager)
    return {"status": "Disruption simulation started"}
