import './LeadCard.css'

function ScoreBar({ points, max }) {
  const pct = max > 0 ? Math.round((points / max) * 100) : 0
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="score-bar-label">{points}/{max}</span>
    </div>
  )
}

function WalkRing({ score, label, color }) {
  if (score == null) return null
  const pct = Math.min(score, 100)
  const r = 28
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  return (
    <div className="walk-ring-wrap">
      <svg width="70" height="70" viewBox="0 0 70 70">
        <circle cx="35" cy="35" r={r} fill="none" stroke="#e5e7eb" strokeWidth="6" />
        <circle
          cx="35" cy="35" r={r} fill="none"
          stroke={color} strokeWidth="6"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 35 35)"
        />
        <text x="35" y="39" textAnchor="middle" fontSize="13" fontWeight="700" fill="#111827">{score}</text>
      </svg>
      <span className="walk-ring-label">{label}</span>
    </div>
  )
}

export default function LeadCard({ lead, onClose }) {
  const { name, email, company, city, state, address, enrichment, scoring } = lead
  const census = enrichment?.census ?? {}
  const ws = enrichment?.walkscore ?? {}
  const rc = enrichment?.rentcast ?? {}
  const bd = scoring?.score_breakdown ?? {}
  const hasWalkscore = ws.walk_score != null
  const hasRentcast = rc.found === true || rc.found === false

  function copyEmail() {
    const text = `Subject: ${scoring.outreach_email.subject}\n\n${scoring.outreach_email.body}`
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="card-overlay" onClick={onClose}>
      <div className="card" onClick={(e) => e.stopPropagation()}>
        <button className="card-close" onClick={onClose}>✕</button>

        {scoring?.red_flag && (
          <div className="red-flag-banner">
            <span className="red-flag-icon">⚠</span>
            <span>{scoring.red_flag_reason ?? 'This lead has been flagged for review.'}</span>
          </div>
        )}

        <div className="card-header">
          <div>
            <h2>{name}</h2>
            <p className="card-sub">{company} · {city}, {state}</p>
            <p className="card-email">{email}</p>
          </div>
          {scoring?.score != null && (
            <div className={`score-badge large priority-${scoring.priority?.toLowerCase()}`}>
              <span className="score-num">{scoring.score}</span>
              <span className="score-label">{scoring.priority}</span>
            </div>
          )}
        </div>

        <div className="card-body">
          {/* Score breakdown */}
          {scoring?.score_breakdown && (
            <section>
              <h3>Score Breakdown</h3>
              <div className="breakdown-grid">
                {Object.entries(bd).map(([key, val]) => (
                  <div key={key} className="breakdown-row">
                    <span className="breakdown-name">{key.replace('_', ' ')}</span>
                    <ScoreBar points={val.points} max={val.max} />
                    <span className="breakdown-reason">{val.reason}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Census data */}
          <section>
            <h3>Market Data</h3>
            <div className="stat-grid">
              <div className="stat">
                <span className="stat-label">Population</span>
                <span className="stat-val">{census.population?.toLocaleString() ?? 'N/A'}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Median Income</span>
                <span className="stat-val">{census.median_household_income ? `$${census.median_household_income.toLocaleString()}` : 'N/A'}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Renter Occupied</span>
                <span className="stat-val">{census.renter_occupied_pct != null ? `${census.renter_occupied_pct}%` : 'N/A'}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Address</span>
                <span className="stat-val">{address}</span>
              </div>
            </div>
          </section>

          {/* WalkScore */}
          {hasWalkscore && (
            <section>
              <h3>Property Location</h3>
              <div className="walk-rings">
                <WalkRing score={ws.walk_score}    label={ws.walk_description    ?? 'Walk'}    color="#4f6ef7" />
                <WalkRing score={ws.transit_score} label={ws.transit_description ?? 'Transit'} color="#22c55e" />
                <WalkRing score={ws.bike_score}    label={ws.bike_description    ?? 'Bike'}    color="#f59e0b" />
              </div>
            </section>
          )}

          {/* RentCast address validation */}
          {hasRentcast && (
            <section>
              <h3>Address Validation (RentCast)</h3>
              {rc.found && rc.property_type ? (
                <div className="stat-grid">
                  <div className="stat">
                    <span className="stat-label">Property Type</span>
                    <span className="stat-val">{rc.property_type}</span>
                  </div>
                </div>
              ) : (
                <p className="rentcast-not-found">
                  {rc.found
                    ? 'Property found but no property type returned — needs human verification.'
                    : 'Address not found in RentCast property database — needs human verification.'}
                </p>
              )}
            </section>
          )}

          {/* Insights */}
          {scoring?.insights?.length > 0 && (
            <section>
              <h3>Sales Insights</h3>
              <ul className="insights-list">
                {scoring.insights.map((ins, i) => <li key={i}>{ins}</li>)}
              </ul>
            </section>
          )}

          {/* Outreach email */}
          {scoring?.outreach_email && (
            <section>
              <div className="email-header">
                <h3>Outreach Email</h3>
                <button className="copy-btn" onClick={copyEmail}>Copy</button>
              </div>
              <div className="email-box">
                <p className="email-subject"><strong>Subject:</strong> {scoring.outreach_email.subject}</p>
                <hr />
                <p className="email-body">{scoring.outreach_email.body}</p>
              </div>
            </section>
          )}

          {/* Error state */}
          {scoring?.error && (
            <section>
              <p className="error-msg">Scoring error: {scoring.error}</p>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
