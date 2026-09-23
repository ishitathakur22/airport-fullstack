import asyncio
from data import BOOKINGS, FLIGHTS

async def run_disruption_simulation(manager):
    """
    Simulates a flight cancellation and proactively drafts rebooking 
    options for all affected passengers, pushing them to the dashboard.
    """
    await asyncio.sleep(2) # delay for effect
    
    # 1. Simulate cancellation of Flight 202
    canceled_flight = "AI202"
    if canceled_flight in FLIGHTS:
        FLIGHTS[canceled_flight]["status"] = "Cancelled - Weather"
        
    await manager.broadcast({
        "type": "ALERT",
        "message": f"Flight {canceled_flight} has been cancelled due to weather."
    })
    
    await asyncio.sleep(2)
    
    # 2. Find affected PNRs
    affected_pnrs = [pnr for pnr, b in BOOKINGS.items() if b["flight_no"] == canceled_flight]
    
    # 3. Push proactive drafts for each affected PNR
    for pnr in affected_pnrs:
        booking = BOOKINGS[pnr]
        
        # Simulate agent processing
        draft = {
            "pnr": pnr,
            "passenger": booking["passenger"],
            "action": "Proactive Rebooking Draft",
            "message": "We noticed your flight AI202 was cancelled. Would you like to be rebooked on AI205 at 18:00 for free?"
        }
        
        await manager.broadcast({
            "type": "PROACTIVE_DRAFT",
            "data": draft
        })
        
        await asyncio.sleep(1) # staggered effect
