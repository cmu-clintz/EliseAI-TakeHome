import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import ResultsTable from './components/ResultsTable'
import './App.css'

function buildDownloadCsv(leads) {
  const headers = ['name', 'email', 'company', 'city', 'state', 'score', 'priority', 'insight_1', 'insight_2', 'insight_3', 'email_subject', 'email_body']
  const rows = leads.map(l => {
    const s = l.scoring ?? {}
    const ins = s.insights ?? []
    return [
      l.name, l.email, l.company, l.city, l.state,
      s.score ?? '',
      s.priority ?? '',
      ins[0] ?? '', ins[1] ?? '', ins[2] ?? '',
      s.outreach_email?.subject ?? '',
      (s.outreach_email?.body ?? '').replace(/\n/g, ' '),
    ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')
  })
  return [headers.join(','), ...rows].join('\n')
}

export default function App() {
  const [leads, setLeads] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(file) {
    setLoading(true)
    setError(null)
    setLeads(null)

    const form = new FormData()
    form.append('file', file)

    try {
      const base = import.meta.env.VITE_API_URL ?? ''
      const res = await fetch(`${base}/api/process`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Unknown error')
      setLeads(data.leads)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    const csv = buildDownloadCsv(leads)
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'enriched_leads.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">EliseAI Lead Enrichment</h1>
        <p className="app-subtitle">Upload a lead CSV to enrich, score, and generate outreach — automatically.</p>
      </header>

      {!leads && (
        <UploadPanel onSubmit={handleSubmit} loading={loading} />
      )}

      {loading && (
        <div className="loading-msg">
          <p>Enriching leads with Census data, Wikipedia, and AI scoring…</p>
          <p className="loading-sub">This may take 30–60 seconds for larger files.</p>
        </div>
      )}

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {leads && (
        <>
          <div className="results-controls">
            <button className="back-btn" onClick={() => setLeads(null)}>← Upload new file</button>
          </div>
          <ResultsTable leads={leads} onDownload={handleDownload} />
        </>
      )}
    </div>
  )
}
