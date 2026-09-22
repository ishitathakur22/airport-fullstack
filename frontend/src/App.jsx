import { useEffect, useState } from 'react'

const API = 'http://localhost:8000'

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
  const [route, setRoute] = useState(null) // local override once approved/escalated

  useEffect(() => {
    fetch(`${API}/api/bookings`)
      .then((r) => r.json())
      .then((data) => {
        setBookings(data)
        if (data.length) setSelectedPnr(data[0].pnr)
      })
      .catch(() => {})
  }, [])

  async function sendQuery(queryText) {
    if (!queryText.trim() || !selectedPnr) return
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: queryText, pnr: selectedPnr }),
      })
      const data = await res.json()
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
    const res = await fetch(`${API}/api/approve/${result.request_id}`, { method: 'POST' })
    if (res.ok) setRoute('done')
  }

  async function escalateInstead() {
    if (!result) return
    const res = await fetch(`${API}/api/escalate/${result.request_id}`, { method: 'POST' })
    if (res.ok) setRoute('escalated')
  }

  return (
    <div className="shell">
      <div className="topbar">
        <div className="mark">SkyRoute <span>Ops</span></div>
        <div className="pulse-dot" />
        <span className="pulse-label">Agent online</span>
      </div>

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
                    <span>Confidence</span>
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
        <div className="board-eyebrow">{booking.pnr}</div>
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

  if (query_type === 'flight_status') {
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

  if (query_type === 'cancellation') {
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

  if (query_type === 'rebooking') {
    const options = decision.options || []
    return (
      <>
        <div className="board-eyebrow">{booking.pnr} · original flight {booking.flight_no}</div>
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
      <div className="board-eyebrow">{booking.pnr}</div>
      <div className="board-title">Answer from policy</div>
      <div className="card">{result.citation_text}</div>
    </>
  )
}
