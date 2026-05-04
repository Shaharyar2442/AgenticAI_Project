import React, { useState, useEffect, useRef, useCallback } from 'react'

// ──────────────────────────────────────────────────────────────
// Pipeline phase definitions with their known sub-steps
// ──────────────────────────────────────────────────────────────
const PHASES = [
  {
    id: 'phase1',
    label: 'Story Generation',
    icon: '📝',
    color: '#6c63ff',
    subSteps: [
      'Connecting to Gemini LLM...',
      'Expanding narrative arc...',
      'Writing scene scripts...',
      'Generating character roster...',
      'Validating JSON schema...',
    ],
  },
  {
    id: 'phase2',
    label: 'Audio Synthesis',
    icon: '🎙️',
    color: '#ff6b9d',
    subSteps: [
      'Assigning neural voices to characters...',
      'Synthesising TTS audio per dialogue line...',
      'Generating SRT subtitle files...',
      'Selecting BGM track by scene mood...',
      'Assembling timing manifest...',
    ],
  },
  {
    id: 'phase3',
    label: 'Video Composition',
    icon: '🎬',
    color: '#fbbf24',
    subSteps: [
      'Generating scene background images...',
      'Generating character portrait images...',
      'Applying Ken Burns animation (FFmpeg)...',
      'Attempting lip-sync (SadTalker)...',
      'Overlaying character portraits...',
      'Burning subtitles into video...',
      'Concatenating all scenes...',
    ],
  },
]

const PHASE_ORDER = PHASES.map(p => p.id)

// ──────────────────────────────────────────────────────────────
// Helper: derive phase state from progress log
// ──────────────────────────────────────────────────────────────
function getPhaseState(phaseId, progressLog, currentPhase) {
  const phaseIdx = PHASE_ORDER.indexOf(phaseId)
  const currentIdx = PHASE_ORDER.indexOf(currentPhase)

  const hasComplete = progressLog.some(
    p => p.phase === phaseId && p.status === 'complete'
  )
  if (hasComplete) return 'done'
  if (currentPhase === phaseId) return 'active'
  if (currentIdx > phaseIdx && currentIdx !== -1) return 'done'
  return 'pending'
}

// ──────────────────────────────────────────────────────────────
// Sub-step ticker — simulates/tracks sub-step progress
// ──────────────────────────────────────────────────────────────
function SubStepTicker({ phase, isActive }) {
  const [stepIdx, setStepIdx] = useState(0)

  useEffect(() => {
    if (!isActive) { setStepIdx(0); return }
    const t = setInterval(() => {
      setStepIdx(i => (i + 1) % phase.subSteps.length)
    }, 2400)
    return () => clearInterval(t)
  }, [isActive, phase.subSteps.length])

  if (!isActive) return null

  return (
    <div className="substep-ticker">
      <span className="substep-dot" style={{ background: phase.color }} />
      <span className="substep-text">{phase.subSteps[stepIdx]}</span>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Live log feed component
// ──────────────────────────────────────────────────────────────
function LiveLog({ logs }) {
  const logEndRef = useRef(null)

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  if (logs.length === 0) return null

  return (
    <div className="live-log">
      <div className="live-log-header">
        <span className="live-dot" />
        Live Pipeline Log
      </div>
      <div className="live-log-body">
        {logs.map((entry, i) => (
          <div key={i} className={`log-entry log-${entry.status || 'info'}`}>
            <span className="log-phase">[{entry.phase || 'system'}]</span>
            <span className="log-msg">{entry.message || JSON.stringify(entry)}</span>
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Phase progress card
// ──────────────────────────────────────────────────────────────
function PhaseCard({ phase, state, progressLog }) {
  return (
    <div className={`phase-card phase-${state}`}>
      <div className="phase-card-header">
        <div className="phase-icon-wrap" style={{ '--phase-color': phase.color }}>
          {state === 'done' ? '✅' : state === 'active' ? (
            <span className="phase-spinner">⚙️</span>
          ) : phase.icon}
        </div>
        <div className="phase-info">
          <span className="phase-label">{phase.label}</span>
          <span className={`phase-state-badge phase-badge-${state}`}>
            {state === 'done' ? 'Complete' : state === 'active' ? 'Running' : 'Waiting'}
          </span>
        </div>
      </div>
      <SubStepTicker phase={phase} isActive={state === 'active'} />
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Version history item
// ──────────────────────────────────────────────────────────────
function VersionItem({ v, isCurrent, onRevert, reverting }) {
  const desc = v.description || `Snapshot v${v.version}`
  const time = v.created_at ? new Date(v.created_at + 'Z').toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : ''

  return (
    <div className={`version-item ${isCurrent ? 'version-current' : ''}`}>
      <div className="version-meta">
        <span className="version-number">v{v.version}</span>
        {isCurrent && <span className="version-current-badge">Current</span>}
        <span className="version-desc">{desc}</span>
        {time && <span className="version-time">{time}</span>}
      </div>
      {!isCurrent && (
        <button
          id={`btn-revert-${v.version}`}
          className="btn-revert"
          onClick={() => onRevert(v.version)}
          disabled={reverting}
        >
          {reverting ? '↩️ Reverting...' : '↩️ Revert'}
        </button>
      )}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────
// Main App
// ──────────────────────────────────────────────────────────────
function App() {
  const [prompt, setPrompt] = useState('')
  const [sessionId] = useState(() => `session_${Date.now()}`)
  const [status, setStatus] = useState('idle')   // idle | running | editing | complete | error
  const [progress, setProgress] = useState([])
  const [videoUrl, setVideoUrl] = useState(null)
  const [editQuery, setEditQuery] = useState('')
  const [versions, setVersions] = useState([])
  const [storyTitle, setStoryTitle] = useState('')
  const [reverting, setReverting] = useState(false)
  const [editFeedback, setEditFeedback] = useState(null)
  const wsRef = useRef(null)

  // Current phase from latest WS message
  const currentPhase = progress.length > 0 ? progress[progress.length - 1]?.phase : null

  // ── WebSocket ──────────────────────────────────────────────
  useEffect(() => {
    if (status !== 'running' && status !== 'editing') return

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
  }, [status, sessionId])

  // ── API helpers ────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/status/${sessionId}`)
      const data = await res.json()
      if (data.status === 'complete') {
        // Use the clean video_url injected by the backend (avoids Windows path issues)
        if (data.video_url) {
          setVideoUrl(data.video_url)
        } else if (data.state?.final_video_path) {
          // Fallback: normalise Windows backslashes and extract relative path
          const raw = data.state.final_video_path.replace(/\\/g, '/')
          const match = raw.match(/outputs\/(.+)$/)
          if (match) setVideoUrl(`/outputs/${match[1]}`)
        }
        setStoryTitle(data.state?.story?.title || 'Generated Video')
        setStatus('complete')
        fetchVersions()
      } else if (data.status === 'error') {
        setStatus('error')
      }
    } catch (e) { /* ignore */ }
  }, [sessionId])

  const fetchVersions = useCallback(async () => {
    try {
      const res = await fetch(`/api/versions/${sessionId}`)
      const data = await res.json()
      setVersions(data.versions || [])
    } catch (e) { /* ignore */ }
  }, [sessionId])

  // ── Handlers ───────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setStatus('running')
    setProgress([])
    setVideoUrl(null)
    setVersions([])
    setEditFeedback(null)

    try {
      await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, session_id: sessionId }),
      })

      // Polling fallback (WebSocket is primary)
      const poller = setInterval(async () => {
        await fetchStatus()
      }, 5000)
      setTimeout(() => clearInterval(poller), 600000)
    } catch (e) {
      setStatus('error')
    }
  }

  const handleEdit = async () => {
    if (!editQuery.trim()) return
    setStatus('editing')
    setEditFeedback(null)
    const query = editQuery
    setEditQuery('')

    try {
      await fetch('/api/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
      })
      setEditFeedback({ type: 'success', msg: `Edit applied: "${query}"` })
      await fetchStatus()
      await fetchVersions()
    } catch (e) {
      setStatus('error')
    }
  }

  const handleRevert = async (version) => {
    setReverting(true)
    try {
      await fetch(`/api/revert/${version}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
      setEditFeedback({ type: 'success', msg: `Reverted to version ${version}` })
      await fetchStatus()
      await fetchVersions()
    } catch (e) {
      setEditFeedback({ type: 'error', msg: 'Revert failed. Try again.' })
    } finally {
      setReverting(false)
    }
  }

  const currentVersion = versions.length > 0 ? Math.max(...versions.map(v => v.version)) : null

  // ── Render ─────────────────────────────────────────────────
  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="header">
        <div className="header-badge">Agentic AI Pipeline</div>
        <h1>🎬 AI Video Generator</h1>
        <p>From a single prompt to a complete animated short film — powered by LLM agents</p>
      </header>

      {/* ── Prompt Input ── */}
      <section className="prompt-section" id="prompt-section">
        <div className="prompt-input-container">
          <label className="prompt-label">Your Story Idea</label>
          <textarea
            id="prompt-input"
            className="prompt-input"
            placeholder="Describe your animated film... e.g., 'A young astronaut discovers a hidden ocean on Mars'"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleGenerate() } }}
            disabled={status === 'running' || status === 'editing'}
            rows={3}
          />
          <button
            id="btn-generate"
            className="btn-generate"
            onClick={handleGenerate}
            disabled={status === 'running' || status === 'editing' || !prompt.trim()}
          >
            {status === 'running' ? (
              <><span className="btn-spinner" />  Generating Pipeline...</>
            ) : '✨ Generate Video'}
          </button>
        </div>
      </section>

      {/* ── Pipeline Progress ── */}
      {(status === 'running' || status === 'editing') && (
        <section className="progress-section" id="progress-section">

          {/* Phase overview cards */}
          <div className="phases-grid">
            {PHASES.map(phase => (
              <PhaseCard
                key={phase.id}
                phase={phase}
                state={getPhaseState(phase.id, progress, currentPhase)}
                progressLog={progress}
              />
            ))}
          </div>

          {/* Live log feed */}
          <LiveLog logs={progress} />
        </section>
      )}

      {/* ── Video Player ── */}
      {videoUrl && (
        <section className="video-section" id="video-section">
          <div className="video-card">
            <div className="video-header">
              <span className="video-title">{storyTitle}</span>
              <span className="status-badge complete">✅ Complete</span>
            </div>
            <video controls autoPlay src={videoUrl} key={videoUrl}>
              Your browser does not support video playback.
            </video>
            <div className="video-actions">
              <a
                id="btn-download"
                className="btn-download"
                href={videoUrl}
                download="generated_video.mp4"
              >
                ⬇ Download MP4
              </a>
            </div>
          </div>
        </section>
      )}

      {/* ── Edit Panel ── (shown after video generated) */}
      {(status === 'complete' || status === 'editing') && (
        <section className="edit-section" id="edit-section">
          <div className="edit-card">
            <div className="edit-card-header">
              <h3>✏️ Edit Your Video</h3>
              <span className="edit-hint">Use natural language — the AI agent classifies your intent</span>
            </div>

            <div className="edit-examples">
              {[
                'Make scene 2 darker',
                'Change voice tone to whisper',
                'Add epic background music',
                'Make it black and white',
              ].map(ex => (
                <button
                  key={ex}
                  className="edit-example-chip"
                  onClick={() => setEditQuery(ex)}
                >
                  {ex}
                </button>
              ))}
            </div>

            <div className="edit-input-row">
              <input
                id="edit-input"
                className="edit-input"
                placeholder="e.g., 'Regenerate the script with a happier tone'"
                value={editQuery}
                onChange={(e) => setEditQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleEdit() }}
                disabled={status === 'editing'}
              />
              <button
                id="btn-edit"
                className="btn-edit"
                onClick={handleEdit}
                disabled={!editQuery.trim() || status === 'editing'}
              >
                {status === 'editing' ? '⏳ Applying...' : 'Apply Edit →'}
              </button>
            </div>

            {editFeedback && (
              <div className={`edit-feedback edit-feedback-${editFeedback.type}`}>
                {editFeedback.type === 'success' ? '✅' : '❌'} {editFeedback.msg}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Version History / Undo Panel ── */}
      {versions.length > 0 && (
        <section className="versions-section" id="versions-section">
          <div className="versions-card">
            <div className="versions-header">
              <h3>📋 Version History</h3>
              <span className="versions-count">{versions.length} snapshot{versions.length !== 1 ? 's' : ''}</span>
            </div>
            <p className="versions-hint">
              Revert to any previous state — all assets are fully restored, nothing is deleted.
            </p>
            <div className="versions-list">
              {[...versions].reverse().map(v => (
                <VersionItem
                  key={v.version}
                  v={v}
                  isCurrent={v.version === currentVersion}
                  onRevert={handleRevert}
                  reverting={reverting}
                />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Error State ── */}
      {status === 'error' && (
        <div className="error-card" id="error-card">
          <span className="error-icon">⚠️</span>
          <div>
            <strong>Pipeline Error</strong>
            <p>Something went wrong. Check the backend terminal for details, then try again.</p>
          </div>
          <button className="btn-generate" style={{ maxWidth: 200 }} onClick={() => setStatus('idle')}>
            Try Again
          </button>
        </div>
      )}

    </div>
  )
}

export default App
