"""
Mock data for the AI Airport Support Agent.
Replace with real DB (SQLite) later if you want persistence across runs.
"""

# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------
BOOKINGS = {
    "PNR1042": {
        "pnr": "PNR1042",
        "passenger": "Priya Sharma",
        "flight_no": "6E202",
        "route": "DEL to BOM",
        "fare_class": "Economy Saver",
        "booking_date": "2026-08-10",
        "flight_date": "2026-09-20",
        "amount_paid": 4250,
        "status": "confirmed",
    },
    "PNR2077": {
        "pnr": "PNR2077",
        "passenger": "Rohan Verma",
        "flight_no": "AI815",
        "route": "BLR to DEL",
        "fare_class": "Business Flex",
        "booking_date": "2026-09-01",
        "flight_date": "2026-09-18",
        "amount_paid": 18500,
        "status": "confirmed",
    },
    "PNR3390": {
        "pnr": "PNR3390",
        "passenger": "Anjali Nair",
        "flight_no": "6E874",
        "route": "MAA to HYD",
        "fare_class": "Economy Basic",
        "booking_date": "2026-09-12",
        "flight_date": "2026-09-14",
        "amount_paid": 2100,
        "status": "confirmed",
    },
}

# ---------------------------------------------------------------------------
# Flights (live status board)
# ---------------------------------------------------------------------------
FLIGHTS = {
    "6E202": {"flight_no": "6E202", "route": "DEL to BOM", "scheduled": "14:30", "status": "On time"},
    "AI815": {"flight_no": "AI815", "route": "BLR to DEL", "scheduled": "09:15", "status": "Delayed by 45 min"},
    "6E874": {"flight_no": "6E874", "route": "MAA to HYD", "scheduled": "18:00", "status": "Cancelled"},
}

# Alternate flights offered when rebooking is needed
REBOOKING_OPTIONS = {
    "6E874": [
        {"flight_no": "6E876", "route": "MAA to HYD", "departure": "20:30", "seats_left": 12},
        {"flight_no": "AI220", "route": "MAA to HYD", "departure": "07:45 (+1 day)", "seats_left": 4},
    ]
}

# ---------------------------------------------------------------------------
# Policy knowledge base (chunks used for retrieval + citation)
# Each chunk simulates a section of a policy PDF, like the ones you'd index
# with FAISS in the full version.
# ---------------------------------------------------------------------------
POLICY_CHUNKS = [
    {
        "id": "cancel-2.1",
        "doc": "Cancellation Policy",
        "section": "Section 2.1",
        "text": (
            "Passengers may cancel a booking up to 24 hours before scheduled "
            "departure for a full refund minus a processing fee of 10% of the "
            "fare. Cancellations within 24 hours of departure are non-refundable "
            "unless the fare class is Business Flex or higher."
        ),
    },
    {
        "id": "cancel-2.3",
        "doc": "Cancellation Policy",
        "section": "Section 2.3",
        "text": (
            "Business Flex and above fare classes may be cancelled at any time "
            "before departure for a full refund with no processing fee."
        ),
    },
    {
        "id": "refund-3.2",
        "doc": "Refund Policy",
        "section": "Section 3.2",
        "text": (
            "Approved refunds are processed to the original payment method "
            "within 5-7 business days. Refunds above Rs 10,000 require manual "
            "review by a support supervisor before processing."
        ),
    },
    {
        "id": "delay-4.1",
        "doc": "Delay & Cancellation Compensation Policy",
        "section": "Section 4.1",
        "text": (
            "If a flight is delayed more than 3 hours or cancelled by the "
            "airline, passengers are entitled to a free rebooking on the next "
            "available flight, or a full refund if no suitable alternative "
            "exists within 24 hours."
        ),
    },
    {
        "id": "baggage-5.4",
        "doc": "Baggage Policy",
        "section": "Section 5.4",
        "text": (
            "Claims for delayed baggage are handled automatically if the bag "
            "is located within 96 hours. Claims for lost or damaged baggage "
            "require manual assessment and are not eligible for automatic "
            "compensation."
        ),
    },
    {
        "id": "assist-6.2",
        "doc": "Special Assistance Policy",
        "section": "Section 6.2",
        "text": (
            "All requests involving wheelchair assistance, unaccompanied "
            "minors, or medical accommodations must be confirmed by a human "
            "support agent at least 48 hours before departure and cannot be "
            "auto-approved."
        ),
    },
    {
        "id": "payment-7.1",
        "doc": "Payment & Billing Policy",
        "section": "Section 7.1",
        "text": (
            "Any report of duplicate charges, unauthorized transactions, or "
            "payment discrepancies must be escalated to the billing team for "
            "manual verification against the payment gateway logs."
        ),
    },
]
