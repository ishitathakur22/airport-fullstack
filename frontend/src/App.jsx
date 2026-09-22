import { useEffect, useState, useRef } from 'react'

const API = 'http://localhost:8000'
const WS_URL = 'ws://localhost:8000/api/ws'

const EXAMPLES = [
  "What's the status of my flight?",
  'I want to cancel my ticket',
  'My flight got cancelled, rebook me',
  'I was charged twice for my ticket',
  'Do I need to confirm wheelchair assistance?',
]

function tierClass(prefix, risk) {
  const map = { low: 'low', medium: 'medium', high: 'high' }
  return `${prefix}-${map[risk] || 'high'}`
}

export default function App() {
  const [bookings, setBookings] = useState([])
  const [selectedPnr, setSelectedPnr] = useState(null)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [route, setRoute] = useState(null) 
  const [alerts, setAlerts] = useState([])
  
  const ws = useRef(null)

  useEffect(() => {
    // Initial fetch
    fetch(`${API}/api/bookings`)
      .then((r) => r.json())
      .then((data) => {
        setBookings(data)
        if (data.length) setSelectedPnr(data[0].pnr)
      })
      .catch(() => {})

    // Connect WebSocket
    ws.current = new WebSocket(WS_URL)
    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      console.log("WS Event:", msg)
      
      if (msg.type === 'NEW_QUERY') {
        setResult(msg.data)
        setRoute(msg.data.route)
        if (msg.data.booking?.pnr) setSelectedPnr(msg.data.booking.pnr)
      } else if (msg.type === 'PROACTIVE_DRAFT') {
        setResult({
          query_type: 'proactive',
          decision: {
             reasoning: 'Proactive intervention initiated by Disruption Engine',
             confidence: 0.99,
             risk: 'medium'
          },
          booking: { pnr: msg.data.pnr, passenger: msg.data.passenger, flight_no: 'AI202' }, // mock info for demo
          log: [
            { step: 'System Alert', detail: 'Disruption engine detected flight cancellation' },
            { step: 'Draft Generated', detail: msg.data.message }
          ],
          citation: 'Ops Policy 4.1',
          citation_text: 'In event of weather cancellation, rebook automatically and notify passenger.',
          route: 'approval',
          request_id: 'proactive-' + msg.data.pnr
        })
        setRoute('approval')
        setSelectedPnr(msg.data.pnr)
      } else if (msg.type === 'STATUS_UPDATE') {
        // If we get a status update for the active result, update the route
        setRoute(msg.status)
      } else if (msg.type === 'ALERT') {
        setAlerts((prev) => [...prev, msg.message])
      }
    }

    return () => {
      if (ws.current) ws.current.close()
    }
  }, [])

  async function sendQuery(queryText) {
    if (!queryText.trim() || !selectedPnr) return
    setLoading(true)
    try {
      // The HTTP call will trigger a WS broadcast back to us, but we can also just wait for the HTTP response
      const res = await fetch(`${API}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: queryText, pnr: selectedPnr }),
      })
      const data = await res.json()
      // WebSockets handles the result update globally now, but we can update local state too
      setResult(data)
      setRoute(data.route)
      setText('')
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function approve() {
    if (!result) return
    // In proactive case, we mock the approval for demo
    if (result.query_type === 'proactive') {
       setRoute('done')
       return
    }
    const res = await fetch(`${API}/api/approve/${result.request_id}`, { method: 'POST' })
    if (res.ok) setRoute('done')
  }

  async function escalateInstead() {
    if (!result) return
    if (result.query_type === 'proactive') {
        setRoute('escalated')
        return
    }
    const res = await fetch(`${API}/api/escalate/${result.request_id}`, { method: 'POST' })
    if (res.ok) setRoute('escalated')
  }

  async function simulateDisruption() {
    await fetch(`${API}/api/simulate_disruption`, { method: 'POST' })
    setAlerts((prev) => [...prev, "Simulation triggered. Wait 2 seconds..."])
  }

  return (
    <div className="shell">
      <div className="topbar">
        <div className="mark">SkyRoute <span>Ops</span></div>
        <div className="pulse-dot" />
        <span className="pulse-label">Agent online (WS Connected)</span>
        <div style={{ flex: 1 }} />
        <button onClick={simulateDisruption} className="btn danger" style={{ padding: '4px 10px', fontSize: 12 }}>
           Simulate Disruption
        </button>
      </div>

      {alerts.length > 0 && (
         <div style={{ background: '#f0ac4a', color: '#000', padding: 8, fontSize: 14, fontWeight: 'bold' }}>
            {alerts[alerts.length - 1]}
         </div>
      )}

      <div className="body-grid">
        <div className="rail">
          <div>
            <div className="rail-label">BOOKING</div>
            <div className="pnr-list" style={{ marginTop: 8 }}>
              {bookings.map((b) => (
                <button
                  key={b.pnr}
                  className={`pnr-chip ${b.pnr === selectedPnr ? 'active' : ''}`}
                  onClick={() => setSelectedPnr(b.pnr)}
                >
                  <span className="code">{b.pnr}</span>
                  <span className="who">{b.passenger.split(' ')[0]}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="query-box">
            <div className="rail-label">QUERY</div>
            <textarea
              placeholder="Describe the issue…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendQuery(text)
                }
              }}
            />
            <button className="send-btn" disabled={loading} onClick={() => sendQuery(text)}>
              {loading ? 'Thinking…' : 'Send'}
            </button>
            <div className="example-row">
              {EXAMPLES.map((ex) => (
                <button key={ex} className="example-chip" onClick={() => sendQuery(ex)}>
                  {ex.length > 28 ? ex.slice(0, 26) + '…' : ex}
                </button>
              ))}
            </div>
          </div>

          <div className="trace">
            <div className="rail-label" style={{ marginBottom: 10 }}>AGENT ACTIVITY</div>
            {!result ? (
              <div className="trace-empty">No activity yet — send a query above.</div>
            ) : (
              <>
                {result.log.map((item, i) => (
                  <div className="trace-step" key={i}>
                    <span className="idx">{String(i + 1).padStart(2, '0')}</span>
                    <div className="content">
                      <div className="step-title">{item.step}</div>
                      <div className="step-detail">{item.detail}</div>
                    </div>
                  </div>
                ))}

                <div className="confidence-block">
                  <div className="confidence-head">
                    <span>Confidence (Local LLM)</span>
                    <span className={tierClass('tier', result.decision.risk)}>
                      {Math.round(result.decision.confidence * 100)}%
                    </span>
                  </div>
                  <div className="confidence-track">
                    <div
                      className={`confidence-fill ${tierClass('fill', result.decision.risk)}`}
                      style={{ width: `${result.decision.confidence * 100}%` }}
                    />
                  </div>
                  <div className="confidence-note">{result.decision.reasoning}</div>
                  <div className="citation-line">based on: {result.citation}</div>
                </div>

                {route === 'approval' && (
                  <>
                    <span className="status-tag pending">Pending approval</span>
                    <div className="action-row">
                      <button className="btn primary" onClick={approve}>Approve</button>
                      <button className="btn danger" onClick={escalateInstead}>Escalate</button>
                    </div>
                  </>
                )}
                {route === 'escalate' && <span className="status-tag escalated">Escalated</span>}
                {route === 'escalated' && <span className="status-tag escalated">Escalated by you</span>}
                {route === 'done' && <span className="status-tag done">Completed</span>}
                {route === 'auto' && <span className="status-tag done">Auto-resolved</span>}
              </>
            )}
          </div>
        </div>

        <div className="board">
          <Board result={result} route={route} bookings={bookings} />
        </div>
      </div>
    </div>
  )
}

function Board({ result, route, bookings }) {
  if (!result) {
    return (
      <>
        <div className="board-eyebrow">Overview</div>
        <div className="board-title">Active bookings</div>
        <div className="roster">
          {bookings.map((b) => (
            <div className="roster-row" key={b.pnr}>
              <div>
                <div className="pnr">{b.pnr}</div>
                <div className="name">{b.passenger}</div>
              </div>
              <div className="route">{b.route} · {b.flight_no}</div>
            </div>
          ))}
        </div>
        <p className="board-empty" style={{ marginTop: 20 }}>
          Pick a booking on the left and send a query — the agent will open
          the relevant page here, the same way it would act on a real
          support console.
        </p>
      </>
    )
  }

  const { query_type, decision, booking, flight } = result

  if ((route === 'escalate' || route === 'escalated')) {
    return (
      <>
        <div className="board-eyebrow">{booking?.pnr}</div>
        <div className="board-title">Escalated to a human agent</div>
        <div className="escalation-banner">
          <div className="label">Reason</div>
          <div className="reason">{decision.reasoning}</div>
        </div>
        <p className="board-empty" style={{ marginTop: 16 }}>
          No automated action was taken on this case.
        </p>
      </>
    )
  }

  if (query_type === 'flight_status' && flight) {
    const dot = flight.status === 'On time' ? '#4fd8c4' : flight.status.includes('Delayed') ? '#f0ac4a' : '#ef6a63'
    return (
      <>
        <div className="board-eyebrow">{booking.pnr} · {booking.passenger}</div>
        <div className="board-title">Flight status</div>
        <div className="card">
          <div className="flight-code">{flight.flight_no}</div>
          <div className="flight-route">{flight.route} · scheduled {flight.scheduled}</div>
          <div className="status-line">
            <span className="status-dot" style={{ background: dot }} />
            {flight.status}
          </div>
        </div>
      </>
    )
  }

  if (query_type === 'cancellation' && booking) {
    return (
      <>
        <div className="board-eyebrow">{booking.pnr}</div>
        <div className="board-title">Cancel booking</div>
        <div className="card">
          <div className="kv-grid">
            <div><div className="k">Passenger</div><div className="v">{booking.passenger}</div></div>
            <div><div className="k">Route</div><div className="v mono">{booking.route}</div></div>
            <div><div className="k">Fare class</div><div className="v">{booking.fare_class}</div></div>
            <div><div className="k">Amount paid</div><div className="v mono">Rs {booking.amount_paid}</div></div>
          </div>
          {decision.refund_amount != null && (
            <>
              <div className="big-number">Rs {decision.refund_amount}</div>
              <div className="big-number-label">proposed refund</div>
            </>
          )}
          {route === 'done' && <span className="status-tag done">Refund issued</span>}
        </div>
      </>
    )
  }

  if (query_type === 'rebooking' || query_type === 'proactive') {
    const options = decision.options || [{flight_no: 'AI205', route: 'BOM-DEL', departure: '18:00', seats_left: 4}]
    return (
      <>
        <div className="board-eyebrow">{booking?.pnr} · original flight {booking?.flight_no}</div>
        <div className="board-title">Rebooking options</div>
        {options.length === 0 && <p className="board-empty">No alternate flights found for this route.</p>}
        {options.map((opt) => (
          <div className="option-card" key={opt.flight_no}>
            <div>
              <div className="code">{opt.flight_no}</div>
              <div className="meta">{opt.route} · departs {opt.departure}</div>
            </div>
            <div className="seats">{opt.seats_left} seats left</div>
          </div>
        ))}
        {route === 'done' && <span className="status-tag done">Rebooked onto {options[0]?.flight_no}</span>}
      </>
    )
  }

  return (
    <>
      <div className="board-eyebrow">{booking?.pnr}</div>
      <div className="board-title">Answer from policy</div>
      <div className="card">{result.citation_text}</div>
    </>
  )
}
