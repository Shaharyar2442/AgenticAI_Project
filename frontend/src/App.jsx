import React, { useState, useEffect, useRef } from 'react'

const PHASES = [
  { id: 'phase1', label: 'Story Generation', icon: '📝' },
  { id: 'phase2', label: 'Audio Synthesis', icon: '🎙️' },
  { id: 'phase3', label: 'Video Composition', icon: '🎬' },
]

function App() {
  const [prompt, setPrompt] = useState('')
  const [sessionId] = useState(() => `session_${Date.now()}`)
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState([])
  const [videoUrl, setVideoUrl] = useState(null)
  const [editQuery, setEditQuery] = useState('')
  const [versions, setVersions] = useState([])
  const [storyTitle, setStoryTitle] = useState('')
  const wsRef = useRef(null)

  // WebSocket connection
  useEffect(() => {
    if (status === 'running' || status === 'editing') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/progress/${sessionId}`)
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        setProgress(prev => [...prev, msg])
        if (msg.status === 'complete' || msg.phase === 'done') {
          fetchStatus()
          fetchVersions()
        }
      }
      ws.onerror = () => console.error('WebSocket error')
      wsRef.current = ws
      return () => ws.close()
    }
  }, [status, sessionId])

  const fetchStatus = async () => {
    try {
      const res = await fetch(`/api/status/${sessionId}`)
      const data = await res.json()
      if (data.status === 'complete' && data.state?.final_video_path) {
        const videoPath = data.state.final_video_path.split('outputs/').pop()
        setVideoUrl(`/outputs/${videoPath}`)
        setStoryTitle(data.state?.story?.title || 'Generated Video')
        setStatus('complete')
      } else if (data.status === 'error') {
        setStatus('error')
      }
    } catch (e) { /* polling fallback */ }
  }

  const fetchVersions = async () => {
    try {
      const res = await fetch(`/api/versions/${sessionId}`)
      const data = await res.json()
      setVersions(data.versions || [])
    } catch (e) { /* ignore */ }
  }

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setStatus('running')
    setProgress([])
    setVideoUrl(null)

    try {
      await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, session_id: sessionId })
      })
      // Poll for completion as fallback
      const poller = setInterval(async () => {
        await fetchStatus()
        if (['complete', 'error'].includes(status)) clearInterval(poller)
      }, 5000)
      setTimeout(() => clearInterval(poller), 300000)
    } catch (e) {
      setStatus('error')
    }
  }

  const handleEdit = async () => {
    if (!editQuery.trim()) return
    setStatus('editing')
    try {
      await fetch('/api/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: editQuery, session_id: sessionId })
      })
      setEditQuery('')
    } catch (e) {
      setStatus('error')
    }
  }

  const handleRevert = async (version) => {
    try {
      await fetch(`/api/revert/${version}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      })
      setStatus('complete')
      await fetchStatus()
      await fetchVersions()
    } catch (e) { /* ignore */ }
  }

  const currentPhase = progress.length > 0 ? progress[progress.length - 1]?.phase : null

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>🎬 AI Video Generator</h1>
        <p>Transform your ideas into animated short films with AI agents</p>
      </header>

      {/* Prompt Input */}
      <section className="prompt-section" id="prompt-section">
        <div className="prompt-input-container">
          <textarea
            id="prompt-input"
            className="prompt-input"
            placeholder="Describe your animated film... e.g., 'A young astronaut discovers a hidden ocean on Mars'"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleGenerate(); }}}
            disabled={status === 'running'}
          />
          <button
            id="btn-generate"
            className="btn-generate"
            onClick={handleGenerate}
            disabled={status === 'running' || status === 'editing' || !prompt.trim()}
          >
            {status === 'running' ? '⏳ Generating...' : '✨ Generate Video'}
          </button>
        </div>
      </section>

      {/* Progress */}
      {(status === 'running' || status === 'editing') && (
        <section className="progress-section" id="progress-section">
          <div className="progress-card">
            <h3>Pipeline Progress</h3>
            {PHASES.map(phase => {
              const isDone = progress.some(p => p.phase === phase.id && (p.status === 'complete' || progress.some(pp => pp.phase !== phase.id && PHASES.findIndex(x => x.id === pp.phase) > PHASES.findIndex(x => x.id === phase.id))))
              const isActive = currentPhase === phase.id
              return (
                <div key={phase.id} className={`progress-item ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}`}>
                  <span className="progress-dot"></span>
                  <span>{phase.icon} {phase.label}</span>
                  {isDone && <span style={{marginLeft: 'auto'}}>✅</span>}
                  {isActive && <span className="status-badge running" style={{marginLeft: 'auto'}}>Running</span>}
                </div>
              )
            })}
            {status === 'editing' && (
              <div className="progress-item active">
                <span className="progress-dot"></span>
                <span>✏️ Applying Edit...</span>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Video Player */}
      {videoUrl && status === 'complete' && (
        <section className="video-section" id="video-section">
          <div className="video-card">
            <video controls autoPlay src={videoUrl}>
              Your browser does not support video playback.
            </video>
            <div className="video-info">
              <span className="video-title">{storyTitle}</span>
              <span className="status-badge complete">Complete</span>
            </div>
          </div>
        </section>
      )}

      {/* Edit Panel */}
      {status === 'complete' && (
        <section className="edit-section" id="edit-section">
          <div className="edit-card">
            <h3>✏️ Edit Video</h3>
            <div className="edit-input-row">
              <input
                id="edit-input"
                className="edit-input"
                placeholder="e.g., 'Make scene 2 darker' or 'Change the narrator's voice'"
                value={editQuery}
                onChange={(e) => setEditQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleEdit(); }}
              />
              <button id="btn-edit" className="btn-edit" onClick={handleEdit} disabled={!editQuery.trim()}>
                Apply Edit
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Version History */}
      {versions.length > 0 && (
        <section className="versions-section" id="versions-section">
          <div className="versions-card">
            <h3>📋 Version History</h3>
            {versions.map(v => (
              <div key={v.version} className="version-item">
                <div>
                  <span className="version-label">Version {v.version}</span>
                  <span className="version-date">{v.description || ''}</span>
                </div>
                <button className="btn-revert" onClick={() => handleRevert(v.version)}>
                  ↩️ Revert
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="progress-card" style={{borderColor: 'var(--error)'}}>
          <p style={{color: 'var(--error)'}}>❌ An error occurred. Check the console and try again.</p>
        </div>
      )}
    </div>
  )
}

export default App
