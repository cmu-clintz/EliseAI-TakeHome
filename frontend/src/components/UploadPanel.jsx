import { useRef, useState } from 'react'
import './UploadPanel.css'

export default function UploadPanel({ onSubmit, loading }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  function handleFile(f) {
    if (f && f.name.endsWith('.csv')) setFile(f)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  function handleSubmit() {
    if (file && !loading) onSubmit(file)
  }

  return (
    <div className="upload-panel">
      <div
        className={`drop-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {file ? (
          <>
            <span className="file-icon">📄</span>
            <p className="file-name">{file.name}</p>
            <p className="file-hint">Click to change file</p>
          </>
        ) : (
          <>
            <span className="file-icon">⬆️</span>
            <p className="drop-label">Drop your leads CSV here</p>
            <p className="file-hint">or click to browse</p>
          </>
        )}
      </div>

      <button
        className="process-btn"
        onClick={handleSubmit}
        disabled={!file || loading}
      >
        {loading ? <><span className="spinner" /> Enriching leads…</> : 'Process Leads'}
      </button>

      <p className="required-cols">
        Required columns: <code>name, email, company, address, city, state</code>
      </p>
    </div>
  )
}
