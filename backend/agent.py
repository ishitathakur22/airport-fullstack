"""
Core agent logic for the AI Airport Support Agent.

Pipeline: classify -> retrieve policy -> decide action + confidence -> route
(auto / needs approval / escalate) -> execute mock tool.

NOTE ON THE CLASSIFIER:
The classify_query() and decide_action() functions below use simple
keyword rules so the whole thing runs with zero API keys and zero setup.
This is intentional for a fast hackathon starting point.

To upgrade to a real LLM (recommended once the flow works end-to-end):
  - Swap classify_query() for a call to Ollama/Claude that returns
    {query_type, priority, sentiment} as JSON.
  - Swap the confidence number in decide_action() for a self-reported
    confidence from the LLM's structured output.
Everything else (retrieval, routing, mock tools, UI) stays the same.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from data import BOOKINGS, FLIGHTS, REBOOKING_OPTIONS, POLICY_CHUNKS


# ---------------------------------------------------------------------------
# 1. Classification
# ---------------------------------------------------------------------------

QUERY_KEYWORDS = {
    # more specific / higher-priority categories first, since this is
    # simple first-match keyword routing (a real LLM classifier wouldn't
    # need this ordering trick)
    "rebooking": ["rebook", "rebooking", "change my flight", "alternate flight"],
    "special_assistance": ["wheelchair", "unaccompanied minor", "medical assistance", "special assistance"],
    "payment_issue": ["duplicate charge", "charged twice", "payment issue", "billing", "unauthorized charge"],
    "refund_status": ["where is my refund", "refund status", "track my refund"],
    "baggage": ["baggage", "luggage", "bag lost", "bag delayed"],
    "flight_status": ["status", "delayed", "on time", "departure time", "when does my flight"],
    "cancellation": ["cancel", "cancellation", "missed"],
    "policy_question": ["policy", "allowance", "how much can i", "am i allowed", "what is the rule"],
}


def classify_query(text: str) -> str:
    """Return a query_type string based on keyword matching."""
    lowered = text.lower()
    for query_type, keywords in QUERY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return query_type
    return "unknown"


# ---------------------------------------------------------------------------
# 2. Retrieval (TF-IDF stand-in for FAISS + embeddings)
# ---------------------------------------------------------------------------

class PolicyRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.texts = [c["text"] for c in chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform(self.texts)

    def retrieve(self, query: str):
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        best_idx = scores.argmax()
        return self.chunks[best_idx], float(scores[best_idx])


retriever = PolicyRetriever(POLICY_CHUNKS)


# ---------------------------------------------------------------------------
# 3. Mock action tools (fixed functions only -- never let the LLM run
#    arbitrary code; every action the agent can take is listed here).
# ---------------------------------------------------------------------------

def get_booking(pnr: str):
    return BOOKINGS.get(pnr)


def get_flight_status(flight_no: str):
    return FLIGHTS.get(flight_no)


def check_cancellation_eligibility(pnr: str):
    booking = BOOKINGS.get(pnr)
    if not booking:
        return False, "Booking not found"
    if booking["fare_class"].startswith("Business"):
        return True, "Business Flex fare -- cancellable anytime, full refund"
    return True, "Standard fare -- cancellable with 10% processing fee"


def create_refund_request(pnr: str, amount: float):
    return {"pnr": pnr, "refund_amount": amount, "status": "refund_created"}


def get_rebooking_options(flight_no: str):
    return REBOOKING_OPTIONS.get(flight_no, [])


def confirm_rebooking(pnr: str, new_flight_no: str):
    return {"pnr": pnr, "new_flight": new_flight_no, "status": "rebooked"}


def escalate_to_human(reason: str):
    return {"status": "escalated", "reason": reason}


# ---------------------------------------------------------------------------
# 4. Decision loop
# ---------------------------------------------------------------------------

# risk tier per query type -- this is the safety boundary of the whole system
RISK_TIER = {
    "flight_status": "low",
    "refund_status": "low",
    "policy_question": "low",
    "cancellation": "medium",
    "rebooking": "medium",
    "baggage": "medium",
    "special_assistance": "high",
    "payment_issue": "high",
    "unknown": "high",
}


def decide_action(query_type: str, pnr: str | None, retrieval_score: float):
    """
    Returns a dict describing the proposed action, a confidence score,
    the risk tier, and a human-readable reasoning string.
    """
    risk = RISK_TIER.get(query_type, "high")

    # confidence blends how well we understood the query (retrieval_score)
    # with how confidently we classified it -- kept simple on purpose
    base_confidence = 0.55 + 0.4 * retrieval_score
    confidence = round(min(base_confidence, 0.97), 2)

    booking = BOOKINGS.get(pnr) if pnr else None

    if query_type == "flight_status" and booking:
        flight = FLIGHTS.get(booking["flight_no"], {})
        return {
            "action": f"Report status for flight {booking['flight_no']}: {flight.get('status', 'unknown')}",
            "confidence": confidence,
            "risk": risk,
            "reasoning": "Flight status lookup is read-only and low risk.",
        }

    if query_type == "cancellation" and booking:
        eligible, note = check_cancellation_eligibility(pnr)
        fee_pct = 0 if booking["fare_class"].startswith("Business") else 0.10
        refund_amount = round(booking["amount_paid"] * (1 - fee_pct), 2)
        return {
            "action": f"Cancel {pnr} and issue refund of Rs {refund_amount}",
            "confidence": confidence,
            "risk": risk,
            "reasoning": note,
            "refund_amount": refund_amount,
        }

    if query_type == "rebooking" and booking:
        options = get_rebooking_options(booking["flight_no"])
        return {
            "action": f"Offer {len(options)} rebooking option(s) for {pnr}",
            "confidence": confidence,
            "risk": risk,
            "reasoning": "Flight disruption detected -- passenger entitled to free rebooking.",
            "options": options,
        }

    if query_type in ("special_assistance", "payment_issue", "unknown"):
        return {
            "action": "Escalate to human support",
            "confidence": confidence,
            "risk": "high",
            "reasoning": {
                "special_assistance": "Special assistance requests always require human confirmation.",
                "payment_issue": "Payment/billing discrepancies require manual verification.",
                "unknown": "Could not confidently classify this request.",
            }[query_type],
        }

    # fallback: policy question or query type with no booking context
    return {
        "action": "Answer from policy knowledge base",
        "confidence": confidence,
        "risk": "low",
        "reasoning": "General policy question, no account action needed.",
    }


def route_action(decision: dict) -> str:
    """Map a decision to one of: auto, approval, escalate"""
    if decision["risk"] == "high" or decision["confidence"] < 0.6:
        return "escalate"
    if decision["risk"] == "medium":
        return "approval"
    return "auto"


def run_pipeline(user_text: str, pnr: str | None):
    """Full agent loop for one incoming query. Returns a log of steps plus
    the final decision and routing outcome -- everything the UI needs."""
    log = []

    query_type = classify_query(user_text)
    log.append(("Ticket received", f'"{user_text}"'))

    chunk, score = retriever.retrieve(user_text)
    log.append(("Retrieved policy", f"{chunk['doc']}, {chunk['section']}"))

    if pnr:
        booking = BOOKINGS.get(pnr)
        if booking:
            log.append(("Booking found", f"{pnr} -- {booking['passenger']}, {booking['route']}"))
        else:
            log.append(("Booking lookup", f"{pnr} not found"))

    decision = decide_action(query_type, pnr, score)
    log.append(("Action proposed", decision["action"]))

    route = route_action(decision)
    if route == "auto":
        log.append(("Routing", "Auto-executing (low risk)"))
    elif route == "approval":
        log.append(("Routing", "Awaiting human approval (medium risk)"))
    else:
        log.append(("Routing", f"Escalated -- {decision['reasoning']}"))

    return {
        "query_type": query_type,
        "citation": f"{chunk['doc']}, {chunk['section']}",
        "citation_text": chunk["text"],
        "decision": decision,
        "route": route,
        "log": log,
    }
