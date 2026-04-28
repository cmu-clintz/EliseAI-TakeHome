import { useState } from 'react'
import LeadCard from './LeadCard'
import './ResultsTable.css'

function priorityOrder(p) {
  return p === 'Hot' ? 0 : p === 'Warm' ? 1 : 2
}

export default function ResultsTable({ leads, onDownload }) {
  const [selected, setSelected] = useState(null)
  const [sortBy, setSortBy] = useState('score')

  const sorted = [...leads].sort((a, b) => {
    if (sortBy === 'score') {
      return (b.scoring?.score ?? -1) - (a.scoring?.score ?? -1)
    }
    if (sortBy === 'priority') {
      return priorityOrder(a.scoring?.priority) - priorityOrder(b.scoring?.priority)
    }
    return (a[sortBy] ?? '').localeCompare(b[sortBy] ?? '')
  })

  const hot  = leads.filter(l => l.scoring?.priority === 'Hot').length
  const warm = leads.filter(l => l.scoring?.priority === 'Warm').length
  const cold = leads.filter(l => l.scoring?.priority === 'Cold').length

  return (
    <div className="results-wrap">
      <div className="results-header">
        <div className="summary-pills">
          <span className="pill hot">{hot} Hot</span>
          <span className="pill warm">{warm} Warm</span>
          <span className="pill cold">{cold} Cold</span>
          <span className="pill total">{leads.length} Total</span>
        </div>
        <button className="download-btn" onClick={onDownload}>⬇ Download CSV</button>
      </div>

      <div className="table-wrap">
        <table className="leads-table">
          <thead>
            <tr>
              {[
                ['name', 'Name'],
                ['company', 'Company'],
                ['city', 'City / State'],
                ['score', 'Score'],
                ['priority', 'Priority'],
              ].map(([key, label]) => (
                <th
                  key={key}
                  className={sortBy === key ? 'active' : ''}
                  onClick={() => setSortBy(key)}
                >
                  {label} {sortBy === key && '↓'}
                </th>
              ))}
              <th>Insights</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((lead, i) => {
              const s = lead.scoring ?? {}
              return (
                <tr
                  key={i}
                  className={`lead-row${s.red_flag ? ' flagged-row' : ''}`}
                  onClick={() => setSelected(lead)}
                >
                  <td>
                    <p className="lead-name">{lead.name}</p>
                    <p className="lead-email">{lead.email}</p>
                  </td>
                  <td>{lead.company}</td>
                  <td>{lead.city}, {lead.state}</td>
                  <td>
                    {s.score != null
                      ? <span className="score-num-inline">{s.score}</span>
                      : <span className="score-err">–</span>}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      {s.priority
                        ? <span className={`badge priority-${s.priority.toLowerCase()}`}>{s.priority}</span>
                        : <span className="badge priority-cold">Error</span>}
                      {s.red_flag && <span className="flag-icon" title={s.red_flag_reason}>⚠</span>}
                    </div>
                  </td>
                  <td className="insights-cell">
                    {s.insights?.[0]
                      ? <span className="insight-preview">{s.insights[0].slice(0, 80)}…</span>
                      : <span className="score-err">–</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {selected && <LeadCard lead={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
