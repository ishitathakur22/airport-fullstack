# SkyRoute Ops — AI Airport Support Agent (full stack)

A real backend + frontend version of the agent, replacing the Streamlit
prototype. Same decision loop underneath (`agent.py` / `data.py`), now
served as an API with a proper React console on top.

```
backend/     FastAPI — the agent pipeline, exposed as a REST API
frontend/    React + Vite — chat rail + live "ops board"
```

## Run it

**Backend** (in one terminal):
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend** (in a second terminal):
```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173). Make sure the
backend is running first — the frontend calls `http://localhost:8000`.

## What's different from the Streamlit version

- Real REST API (`/api/query`, `/api/approve/{id}`, `/api/escalate/{id}`,
  `/api/bookings`) instead of everything living inside one Streamlit
  process — this is the actual "full stack" split: a backend you could
  deploy separately from the UI.
- A distinct visual identity instead of default Streamlit styling — an
  airline ops-console look: deep navy surface, monospace for flight/PNR
  codes, risk-tier color language (cyan = auto, amber = needs approval,
  coral = escalated) instead of generic badges.
- Pending decisions are tracked server-side by a request ID, so
  Approve/Escalate calls hit the real backend instead of just flipping
  local UI state.

## Try these in the query box

- "What's the status of my flight?" → auto-resolved
- "I want to cancel my ticket" → needs your approval
- "My flight got cancelled, rebook me" (use PNR3390, its flight is cancelled) → needs your approval
- "I was charged twice for my ticket" → escalated
- "Do I need to confirm wheelchair assistance?" → escalated

## Next upgrades

- **Twilio SMS Webhook**: (Planned) Integrate a Twilio phone number to accept SMS queries, route them to the `/api/webhook/twilio` endpoint, and allow passengers to talk to the AI via text.
- **RAG / Vector Database**: Swap `PolicyRetriever` for FAISS or ChromaDB when you're ready to handle large, complex airline policy documents.

## Deploying for your submission

If your hackathon wants a live link, not just local run instructions:
- Backend: any small host that runs Python (Render, Railway, a free-tier VM).
- Frontend: `npm run build` produces `frontend/dist/` — deploy that as a
  static site (Vercel, Netlify), and update the `API` constant at the
  top of `frontend/src/App.jsx` to your deployed backend URL before building.
