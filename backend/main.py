"""
FastAPI backend for the AI Airport Support Agent.

Wraps the same agent.py / data.py logic used in the Streamlit version,
exposed as a REST API so a real React frontend can talk to it.

Run with:
    uvicorn main:app --reload --port 8000
"""

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data import BOOKINGS, FLIGHTS
from agent import (
    run_pipeline,
    create_refund_request,
    confirm_rebooking,
    escalate_to_human,
)

app = FastAPI(title="Airport Support Agent API")

# Allow the Vite dev server (and any local frontend) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory store for pending decisions, keyed by a request id
# (swap for a real DB/session store if you need this to survive restarts)
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
def submit_query(req: QueryRequest):
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
    }

    return {
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


@app.post("/api/approve/{request_id}")
def approve(request_id: str):
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

    del PENDING[request_id]
    return {"status": "executed", "outcome": outcome}


@app.post("/api/escalate/{request_id}")
def escalate(request_id: str):
    pending = PENDING.get(request_id)
    if not pending:
        raise HTTPException(404, "No pending decision for this request")

    reason = pending["decision"].get("reasoning", "Escalated by user choice")
    outcome = escalate_to_human(reason)
    del PENDING[request_id]
    return outcome
