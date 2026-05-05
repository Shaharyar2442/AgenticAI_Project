import React, { useState, useEffect, useRef, useCallback } from 'react'

const PHASES = [
  { id: 'phase1', label: 'Story Generation', icon: '📜', color: '#c9a44c',
    subSteps: ['Connecting to LLM...','Expanding narrative...','Writing scenes...','Generating characters...','Validating...'] },
  { id: 'phase2', label: 'Audio Synthesis', icon: '🎙️', color: '#8b2d2d',
    subSteps: ['Assigning voices...','Synthesising TTS...','Generating subtitles...','Building timing manifest...'] },
  { id: 'phase3', label: 'Video Composition', icon: '🎬', color: '#6db56d',
    subSteps: ['Generating scene images...','Applying Ken Burns...','Overlaying portraits...','Burning subtitles...','Concatenating...'] },
]
const PHASE_ORDER = PHASES.map(p => p.id)

function getPhaseState(phaseId, progressLog, currentPhase) {
  const phaseIdx = PHASE_ORDER.indexOf(phaseId)
  const currentIdx = PHASE_ORDER.indexOf(currentPhase)
  if (progressLog.some(p => p.phase === phaseId && p.status === 'complete')) return 'done'
  if (currentPhase === phaseId) return 'active'
  if (currentIdx > phaseIdx && currentIdx !== -1) return 'done'
  return 'pending'
}

function SubStepTicker({ phase, isActive }) {
  const [idx, setIdx] = useState(0)
  useEffect(() => {
    if (!isActive) { setIdx(0); return }
    const t = setInterval(() => setIdx(i => (i + 1) % phase.subSteps.length), 2400)
    return () => clearInterval(t)
  }, [isActive, phase.subSteps.length])
  if (!isActive) return null
  return (<div className="substep-ticker"><span className="substep-dot" style={{ background: phase.color }} /><span className="substep-text">{phase.subSteps[idx]}</span></div>)
}

function LiveLog({ logs }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollIntoView({ behavior: 'smooth' }) }, [logs])
  if (!logs.length) return null
  return (
    <div className="live-log">
      <div className="live-log-header"><span className="live-dot" />Live Pipeline Log</div>
      <div className="live-log-body">
        {logs.map((e, i) => (<div key={i} className={`log-entry log-${e.status||'info'}`}><span className="log-phase">[{e.phase||'sys'}]</span><span className="log-msg">{e.message||JSON.stringify(e)}</span></div>))}
        <div ref={ref} />
      </div>
    </div>
  )
}

function PhaseCard({ phase, state }) {
  return (
    <div className={`phase-card phase-${state}`}>
      <div className="phase-card-header">
        <div className="phase-icon-wrap">{state==='done'?'✅':state==='active'?<span className="phase-spinner">⚙️</span>:phase.icon}</div>
        <div className="phase-info">
          <span className="phase-label">{phase.label}</span>
          <span className={`phase-state-badge phase-badge-${state}`}>{state==='done'?'Complete':state==='active'?'Running':'Waiting'}</span>
        </div>
      </div>
      <SubStepTicker phase={phase} isActive={state==='active'} />
    </div>
  )
}

function StoryPanel({ storyData }) {
  const [expanded, setExpanded] = useState(true)
  if (!storyData) return null
  return (
    <div className="story-panel">
      <div className="story-panel-header">
        <h3>📖 Generated Story</h3>
        <button className="story-panel-toggle" onClick={() => setExpanded(!expanded)}>{expanded ? '▲ Collapse' : '▼ Expand'}</button>
      </div>
      {expanded && (<>
        <div className="story-title-display">{storyData.title}</div>
        <div className="story-genre">{storyData.genre}</div>
        <p className="story-synopsis">{storyData.synopsis}</p>
        <div className="story-scenes-list">
          {storyData.scenes?.map(s => (
            <div key={s.scene_id} className="story-scene-item">
              <div className="story-scene-title">{s.scene_id}: {s.title}</div>
              <div className="story-scene-meta">Mood: {s.mood} · {s.dialogue_count} lines · {s.setting?.substring(0,80)}...</div>
            </div>
          ))}
        </div>
      </>)}
    </div>
  )
}

function CharacterGallery({ characters, portraitUrls, sessionId, onPortraitUpdated }) {
  const [accepted, setAccepted] = useState({})
  const [regenerating, setRegenerating] = useState({})
  const [localUrls, setLocalUrls] = useState(portraitUrls)

  useEffect(() => setLocalUrls(portraitUrls), [portraitUrls])

  if (!characters?.length) return null

  const handleRegen = async (charId) => {
    setRegenerating(prev => ({ ...prev, [charId]: true }))
    setAccepted(prev => ({ ...prev, [charId]: false }))
    try {
      const res = await fetch(`/api/regenerate-character/${sessionId}/${charId}`, { method: 'POST' })
      const data = await res.json()
      if (data.portrait_url) {
        setLocalUrls(prev => ({ ...prev, [charId]: data.portrait_url + '?t=' + Date.now() }))
      }
      if (onPortraitUpdated) onPortraitUpdated()
    } catch (e) { console.error(e) }
    finally { setRegenerating(prev => ({ ...prev, [charId]: false })) }
  }

  const allAccepted = characters.every(c => accepted[c.id])

  return (
    <div className="char-gallery">
      <div className="char-gallery-header">⚔ Generated Characters — Review & Accept</div>
      <div className="char-grid">
        {characters.map(c => (
          <div key={c.id} className="char-card">
            {localUrls[c.id] ? (
              <img src={localUrls[c.id]} alt={c.name} />
            ) : (
              <div style={{width:'100%',height:200,background:'var(--bg-secondary)',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text-muted)',fontSize:'0.8rem'}}>Generating...</div>
            )}
            <div className="char-card-body">
              <div className="char-name">{c.name}</div>
              <div className="char-role">{c.role}</div>
              <div className="char-voice">{c.voice_description}</div>
              <div className="char-actions">
                <button className={`btn-char-accept ${accepted[c.id]?'accepted':''}`} onClick={() => setAccepted(p=>({...p,[c.id]:true}))}>
                  {accepted[c.id] ? '✓ Accepted' : 'Accept'}
                </button>
                <button className="btn-char-regen" onClick={() => handleRegen(c.id)} disabled={regenerating[c.id]}>
                  {regenerating[c.id] ? '...' : '↻ Regen'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {allAccepted && (
        <div style={{textAlign:'center',marginTop:'0.5rem',fontSize:'0.8rem',color:'var(--success)'}}>
          All characters accepted ✓
        </div>
      )}
    </div>
  )
}

function VersionItem({ v, isCurrent, onRevert, reverting }) {
  const desc = v.description || `Snapshot v${v.version}`
  const time = v.created_at ? new Date(v.created_at+'Z').toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}) : ''
  return (
    <div className={`version-item ${isCurrent?'version-current':''}`}>
      <div className="version-meta">
        <span className="version-number">v{v.version}</span>
        {isCurrent && <span className="version-current-badge">Current</span>}
        <span className="version-desc">{desc}</span>
        {time && <span className="version-time">{time}</span>}
      </div>
      {!isCurrent && <button className="btn-revert" onClick={()=>onRevert(v.version)} disabled={reverting}>{reverting?'↩ ...':'↩ Revert'}</button>}
    </div>
  )
}

// ──────────────────────────
// Main App
// ──────────────────────────
function App() {
  const [prompt, setPrompt] = useState('')
  const [sessionId] = useState(() => `session_${Date.now()}`)
  // idle | generating_story | characters_ready | running | editing | complete | error
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState([])
  const [videoUrl, setVideoUrl] = useState(null)
  const [editQuery, setEditQuery] = useState('')
  const [versions, setVersions] = useState([])
  const [storyTitle, setStoryTitle] = useState('')
  const [reverting, setReverting] = useState(false)
  const [editFeedback, setEditFeedback] = useState(null)
  const [activeVersion, setActiveVersion] = useState(null)
  const [storyData, setStoryData] = useState(null)
  const [portraitUrls, setPortraitUrls] = useState({})

  const currentPhase = progress.length > 0 ? progress[progress.length-1]?.phase : null

  useEffect(() => {
    const msg = progress.find(p => p.story_data)
    if (msg) setStoryData(msg.story_data)
  }, [progress])

  // WebSocket
  useEffect(() => {
    if (status !== 'generating_story' && status !== 'running' && status !== 'editing') return
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/progress/${sessionId}`)
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      setProgress(prev => [...prev, msg])
      if (msg.status === 'characters_ready') {
        fetchStatus()
      }
      if (msg.status === 'complete' || msg.phase === 'done') {
        fetchStatus()
        fetchVersions()
      }
    }
    ws.onerror = () => console.error('WS error')
    return () => ws.close()
  }, [status, sessionId])

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/status/${sessionId}`)
      const data = await res.json()
      if (data.portrait_urls) setPortraitUrls(data.portrait_urls)
      if (data.status === 'characters_ready') {
        setStoryTitle(data.state?.story?.title || '')
        setStatus('characters_ready')
      } else if (data.status === 'complete') {
        if (data.video_url) setVideoUrl(data.video_url + '?t=' + Date.now())
        else if (data.state?.final_video_path) {
          const raw = data.state.final_video_path.replace(/\\/g,'/')
          const m = raw.match(/outputs\/(.+)$/)
          if (m) setVideoUrl(`/outputs/${m[1]}?t=${Date.now()}`)
        }
        setStoryTitle(data.state?.story?.title || 'Generated Video')
        if (data.state?.version != null) setActiveVersion(data.state.version)
        setStatus('complete')
        fetchVersions()
      } else if (data.status === 'error') {
        setStatus('error')
      }
    } catch(e) {}
  }, [sessionId])

  const fetchVersions = useCallback(async () => {
    try {
      const res = await fetch(`/api/versions/${sessionId}`)
      const data = await res.json()
      setVersions(data.versions || [])
    } catch(e) {}
  }, [sessionId])

  // Stage 1: Generate story + portraits
  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setStatus('generating_story'); setProgress([]); setVideoUrl(null); setVersions([])
    setEditFeedback(null); setStoryData(null); setPortraitUrls({})
    try {
      await fetch('/api/generate', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ prompt, session_id: sessionId })
      })
      const poller = setInterval(() => fetchStatus(), 5000)
      setTimeout(() => clearInterval(poller), 600000)
    } catch(e) { setStatus('error') }
  }

  // Stage 2: Continue after accepting characters
  const handleContinue = async () => {
    setStatus('running')
    try {
      await fetch('/api/continue', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ session_id: sessionId })
      })
      const poller = setInterval(() => fetchStatus(), 5000)
      setTimeout(() => clearInterval(poller), 600000)
    } catch(e) { setStatus('error') }
  }

  const handleEdit = async () => {
    if (!editQuery.trim()) return
    setStatus('editing'); setEditFeedback(null)
    const q = editQuery; setEditQuery('')
    try {
      await fetch('/api/edit', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ query: q, session_id: sessionId })
      })
      setEditFeedback({ type:'success', msg:`Edit applied: "${q}"` })
      await fetchStatus(); await fetchVersions()
    } catch(e) { setStatus('error') }
  }

  const handleRevert = async (v) => {
    setReverting(true)
    try {
      await fetch(`/api/revert/${v}`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ session_id: sessionId })
      })
      setEditFeedback({ type:'success', msg:`Reverted to v${v}` })
      await fetchStatus(); await fetchVersions()
    } catch(e) { setEditFeedback({ type:'error', msg:'Revert failed.' }) }
    finally { setReverting(false) }
  }

  const currentVersion = activeVersion != null ? activeVersion : (versions.length > 0 ? Math.max(...versions.map(v=>v.version)) : null)
  const isProcessing = status === 'generating_story' || status === 'running' || status === 'editing'

  return (
    <div className="app">
      <header className="header">
        <div className="header-badge">Agentic AI Pipeline</div>
        <h1>🎬 AI Video Generator</h1>
        <p>From a single prompt to a complete animated short film — forged by LLM agents</p>
      </header>

      {/* Prompt */}
      <section className="prompt-section" id="prompt-section">
        <div className="prompt-input-container">
          <label className="prompt-label">Your Story Idea</label>
          <textarea id="prompt-input" className="prompt-input"
            placeholder="Describe your animated film..."
            value={prompt} onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => { if (e.key==='Enter'&&!e.shiftKey) { e.preventDefault(); handleGenerate() }}}
            disabled={isProcessing || status === 'characters_ready'} rows={3} />
          <button id="btn-generate" className="btn-generate" onClick={handleGenerate}
            disabled={isProcessing || status === 'characters_ready' || !prompt.trim()}>
            {status === 'generating_story' ? <><span className="btn-spinner" /> Generating Story...</> : '✦ Generate Video'}
          </button>
        </div>
      </section>

      {/* Progress */}
      {isProcessing && (
        <section className="progress-section" id="progress-section">
          <div className="phases-grid">
            {PHASES.map(p => <PhaseCard key={p.id} phase={p} state={getPhaseState(p.id, progress, currentPhase)} />)}
          </div>
          <LiveLog logs={progress} />
        </section>
      )}

      {/* Story panel — shown after Phase 1 */}
      {storyData && <StoryPanel storyData={storyData} />}

      {/* Character gallery — shown when characters_ready, with continue button */}
      {(status === 'characters_ready' || storyData?.characters) && (
        <CharacterGallery characters={storyData?.characters || []} portraitUrls={portraitUrls}
          sessionId={sessionId} onPortraitUpdated={fetchStatus} />
      )}

      {/* Continue button — shown ONLY when characters are ready */}
      {status === 'characters_ready' && (
        <section style={{textAlign:'center', marginBottom:'1.5rem'}}>
          <button className="btn-generate" onClick={handleContinue}
            style={{maxWidth:400, margin:'0 auto'}}>
            ✦ Accept Characters & Continue Pipeline
          </button>
        </section>
      )}

      {/* Video */}
      {videoUrl && (
        <section className="video-section" id="video-section">
          <div className="video-card">
            <div className="video-header">
              <span className="video-title">{storyTitle}</span>
              <span className="status-badge complete">✅ Complete</span>
            </div>
            <video controls autoPlay src={videoUrl} key={videoUrl}>No video support.</video>
            <div className="video-actions">
              <a id="btn-download" className="btn-download" href={videoUrl} download="generated_video.mp4">⬇ Download</a>
            </div>
          </div>
        </section>
      )}

      {/* Edit */}
      {(status === 'complete' || status === 'editing') && (
        <section className="edit-section" id="edit-section">
          <div className="edit-card">
            <div className="edit-card-header">
              <h3>✏️ Edit Your Video</h3>
              <span className="edit-hint">Natural language — the AI classifies your intent</span>
            </div>
            <div className="edit-examples">
              {['Make scene 2 darker','Change voice tone to whisper','Add epic background music','Make it black and white'].map(ex => (
                <button key={ex} className="edit-example-chip" onClick={()=>setEditQuery(ex)}>{ex}</button>
              ))}
            </div>
            <div className="edit-input-row">
              <input id="edit-input" className="edit-input" placeholder="e.g., 'Make the narrator speak faster'"
                value={editQuery} onChange={e=>setEditQuery(e.target.value)}
                onKeyDown={e=>{if(e.key==='Enter')handleEdit()}} disabled={status==='editing'} />
              <button id="btn-edit" className="btn-edit" onClick={handleEdit}
                disabled={!editQuery.trim()||status==='editing'}>
                {status==='editing' ? '⏳ Applying...' : 'Apply Edit →'}
              </button>
            </div>
            {editFeedback && (
              <div className={`edit-feedback edit-feedback-${editFeedback.type}`}>
                {editFeedback.type==='success'?'✅':'❌'} {editFeedback.msg}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Versions */}
      {versions.length > 0 && (
        <section className="versions-section" id="versions-section">
          <div className="versions-card">
            <div className="versions-header">
              <h3>📋 Version History</h3>
              <span className="versions-count">{versions.length} snapshot{versions.length!==1?'s':''}</span>
            </div>
            <p className="versions-hint">Revert to any previous state of this generation.</p>
            <div className="versions-list">
              {[...versions].reverse().map(v => (
                <VersionItem key={v.version} v={v} isCurrent={v.version===currentVersion}
                  onRevert={handleRevert} reverting={reverting} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="error-card" id="error-card">
          <span className="error-icon">⚠️</span>
          <div><strong>Pipeline Error</strong><p>Check the backend terminal, then try again.</p></div>
          <button className="btn-generate" style={{maxWidth:200}} onClick={()=>setStatus('idle')}>Try Again</button>
        </div>
      )}
    </div>
  )
}

export default App
