import { useState, useEffect, useRef, createContext, useContext } from 'react'
import './index.css'

const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.PROD ? 'https://rift-backend-je0t.onrender.com' : 'http://localhost:5000')

/* ========== APP STATE CONTEXT ========== */
const AppContext = createContext()

function AppProvider({ children }) {
  const [repoUrl, setRepoUrl] = useState('https://github.com/Code71590/buggy-calculator')
  const [teamName, setTeamName] = useState('Bubble')
  const [leaderName, setLeaderName] = useState('Ullas A U')
  const [isRunning, setIsRunning] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [events, setEvents] = useState([])
  const [finalResult, setFinalResult] = useState(null)
  const [ciRuns, setCiRuns] = useState([])
  const eventSourceRef = useRef(null)

  const value = {
    repoUrl, setRepoUrl,
    teamName, setTeamName,
    leaderName, setLeaderName,
    isRunning, setIsRunning,
    statusMessage, setStatusMessage,
    events, setEvents,
    finalResult, setFinalResult,
    ciRuns, setCiRuns,
    eventSourceRef,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

function useAppState() {
  return useContext(AppContext)
}


/* ========== MAIN APP ========== */
function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  )
}

function AppInner() {
  const {
    isRunning, setIsRunning,
    setStatusMessage,
    events, setEvents,
    finalResult, setFinalResult,
    ciRuns, setCiRuns,
    eventSourceRef,
    repoUrl, teamName, leaderName,
  } = useAppState()

  const eventsEndRef = useRef(null)

  // Auto-scroll to latest event
  useEffect(() => {
    if (eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [events])

  // Connect to SSE when running
  useEffect(() => {
    if (!isRunning) return

    const es = new EventSource(`${API_BASE}/api/events`)
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('[SSE]', data.type, data)

        if (data.message) {
          setStatusMessage(data.message)
        }

        setEvents(prev => [...prev, { ...data, _ts: new Date().toLocaleTimeString() }])

        // Track CI/CD iterations
        if (data.type === 'iteration_start' || data.type === 'iteration_complete' || data.type === 'test_result') {
          setCiRuns(prev => {
            const updated = [...prev]
            if (data.type === 'iteration_start') {
              updated.push({
                iteration: data.iteration || updated.length + 1,
                status: 'running',
                timestamp: new Date().toLocaleTimeString(),
                passed: 0,
                failed: 0,
              })
            } else if (data.type === 'test_result') {
              if (updated.length > 0) {
                updated[updated.length - 1].passed = data.passed || 0
                updated[updated.length - 1].failed = data.failed || 0
                updated[updated.length - 1].status = data.failed > 0 ? 'failed' : 'passed'
              }
            } else if (data.type === 'iteration_complete') {
              if (updated.length > 0) {
                updated[updated.length - 1].status = data.all_passed ? 'passed' : 'failed'
                updated[updated.length - 1].fixes_applied = data.fixes_applied || 0
              }
            }
            return updated
          })
        }

        // Handle terminal events
        if (data.type === 'done') {
          setIsRunning(false)
          setFinalResult(data.result || data)
          es.close()
        } else if (data.type === 'error') {
          setIsRunning(false)
          es.close()
        }
      } catch (err) {
        console.error('[SSE] Parse error:', err)
      }
    }

    es.onerror = () => {
      console.log('[SSE] Connection error/closed')
    }

    return () => {
      es.close()
    }
  }, [isRunning])

  const handleRun = async () => {
    if (!repoUrl || !teamName || !leaderName) {
      alert('Please fill in all fields')
      return
    }

    setIsRunning(true)
    setFinalResult(null)
    setEvents([])
    setCiRuns([])
    setStatusMessage('Starting agent...')

    try {
      const res = await fetch(`${API_BASE}/api/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          team_name: teamName,
          leader_name: leaderName,
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        alert(err.error || 'Failed to start agent')
        setIsRunning(false)
      }
    } catch (err) {
      alert('Could not connect to backend. Is the server running?')
      setIsRunning(false)
    }
  }

  const result = finalResult?.result || finalResult

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-inner">
          <div className="logo-area">
            <div className="logo">⚡</div>
            <div className="logo-text">
              <h1>CI/CD Healing Agent</h1>
              <span className="subtitle">Autonomous DevOps Agent • RIFT 2026</span>
            </div>
          </div>
          <div className="header-status">
            {isRunning && (
              <div className="header-badge running-badge">
                <span className="pulse-dot" />
                Running
              </div>
            )}
            {result && !isRunning && (
              <div className={`header-badge ${result.final_status === 'PASSED' ? 'passed-badge' : 'failed-badge'}`}>
                {result.final_status === 'PASSED' ? '✓' : '✗'} {result.final_status}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="main-content">
        {/* Input Section */}
        <InputForm onRun={handleRun} />

        {/* Status Bar */}
        {isRunning && <StatusBar />}

        {/* Live Event Feed */}
        {events.length > 0 && (
          <LiveFeed events={events} isRunning={isRunning} eventsEndRef={eventsEndRef} />
        )}

        {/* Final Results Dashboard */}
        {result && (
          <div className="results-dashboard">
            <SummaryCard result={result} />
            <ScoreBreakdownPanel result={result} />
            {ciRuns.length > 0 && <CICDTimeline runs={ciRuns} retryLimit={result.retry_limit || 5} />}
            {result.all_fixes?.length > 0 && <FixesTable fixes={result.all_fixes} />}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <span>CI/CD Healing Agent</span>
        <span className="footer-sep">•</span>
        <span>RIFT 2026 Hackathon</span>
      </footer>
    </div>
  )
}


/* ========== INPUT FORM ========== */
function InputForm({ onRun }) {
  const { repoUrl, setRepoUrl, teamName, setTeamName, leaderName, setLeaderName, isRunning } = useAppState()

  return (
    <section className="card input-section" id="input-section">
      <div className="card-header">
        <span className="card-icon">🔧</span>
        <h2>Configure Agent</h2>
      </div>
      <div className="form-grid">
        <div className="form-group full-width">
          <label htmlFor="repo-url">GitHub Repository URL</label>
          <input
            id="repo-url"
            type="text"
            placeholder="https://github.com/user/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            disabled={isRunning}
          />
        </div>
        <div className="form-group">
          <label htmlFor="team-name">Team Name</label>
          <input
            id="team-name"
            type="text"
            placeholder="e.g., RIFT ORGANISERS"
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            disabled={isRunning}
          />
        </div>
        <div className="form-group">
          <label htmlFor="leader-name">Team Leader Name</label>
          <input
            id="leader-name"
            type="text"
            placeholder="e.g., Saiyam Kumar"
            value={leaderName}
            onChange={(e) => setLeaderName(e.target.value)}
            disabled={isRunning}
          />
        </div>
        <div className="form-group btn-group">
          <button className="btn-run" id="run-agent-btn" onClick={onRun} disabled={isRunning}>
            {isRunning ? (
              <>
                <span className="spinner" />
                Agent Running...
              </>
            ) : (
              <>🚀 Analyze Repository</>
            )}
          </button>
        </div>
      </div>
    </section>
  )
}


/* ========== STATUS BAR ========== */
function StatusBar() {
  const { statusMessage } = useAppState()
  return (
    <div className="status-bar" id="status-bar">
      <div className="pulse-dot" />
      <span className="message">{statusMessage}</span>
    </div>
  )
}


/* ========== LIVE FEED ========== */
function LiveFeed({ events, isRunning, eventsEndRef }) {
  return (
    <section className="card live-feed" id="live-feed">
      <div className="card-header">
        <span className="live-indicator">
          <span className={`live-dot ${isRunning ? 'active' : 'inactive'}`} />
        </span>
        <h2>{isRunning ? 'Live Pipeline Feed' : 'Pipeline Run Complete'}</h2>
        <span className="event-count">{events.length} events</span>
      </div>
      <div className="event-list">
        {events.map((evt, i) => (
          <EventCard key={i} event={evt} />
        ))}
        <div ref={eventsEndRef} />
      </div>
    </section>
  )
}


/* ========== EVENT CARD ========== */
function EventCard({ event }) {
  const { type, _ts } = event

  const getIcon = () => {
    switch (type) {
      case 'step': return '⏳'
      case 'clone': return '📦'
      case 'analysis': return '🔍'
      case 'branch': return '🌿'
      case 'iteration_start': return '🔄'
      case 'test_result': return event.failed > 0 ? '❌' : '✅'
      case 'files_needed': return '📂'
      case 'file_contents': return '📄'
      case 'fixes': return '🔧'
      case 'fix_applied': return '✨'
      case 'commit': return '💾'
      case 'iteration_complete': return '🔁'
      case 'all_passed': return '🎉'
      case 'done': return '🏁'
      case 'error': return '💥'
      case 'no_fixes': return '⚠️'
      case 'no_fixes_applied': return '⚠️'
      case 'max_iterations': return '⏰'
      case 'status': return '📡'
      default: return '📌'
    }
  }

  const getColor = () => {
    switch (type) {
      case 'error':
      case 'no_fixes':
      case 'no_fixes_applied': return 'event-error'
      case 'all_passed':
      case 'done': return 'event-success'
      case 'test_result': return event.failed > 0 ? 'event-warning' : 'event-success'
      case 'fixes':
      case 'fix_applied': return 'event-info'
      case 'step': return 'event-step'
      default: return 'event-default'
    }
  }

  return (
    <div className={`event-card ${getColor()}`}>
      <div className="event-header">
        <span className="event-icon">{getIcon()}</span>
        <span className="event-type">{type.replace(/_/g, ' ').toUpperCase()}</span>
        <span className="event-time">{_ts}</span>
      </div>
      <div className="event-message">{event.message}</div>

      {/* Extended content based on type */}
      {type === 'analysis' && (
        <div className="event-extra">
          <div className="event-detail">
            <span className="detail-label">Language:</span>{' '}
            <span className="detail-value">{event.language}</span>
          </div>
          <div className="event-detail">
            <span className="detail-label">Test Command:</span>{' '}
            <code className="detail-code">{event.test_command}</code>
          </div>
          <div className="event-detail">
            <span className="detail-label">Test Files:</span>{' '}
            <span className="detail-value">{event.test_files?.length || 0} found</span>
          </div>
          {event.tree && (
            <CollapsiblePre title="File Tree" content={event.tree} />
          )}
        </div>
      )}

      {type === 'test_result' && (
        <div className="event-extra">
          <div className="event-stats">
            <span className="stat stat-pass">✅ {event.passed} passed</span>
            <span className="stat stat-fail">❌ {event.failed} failed</span>
            <span className="stat stat-err">🐛 {event.error_count} errors</span>
          </div>
          {event.errors && event.errors.length > 0 && (
            <div className="error-list">
              {event.errors.map((err, i) => (
                <div key={i} className="error-item">
                  <span className="error-test">{err.test_name}</span>
                  <span className="error-file">{err.file}:{err.line}</span>
                  <span className="error-msg">{err.error_message}</span>
                </div>
              ))}
            </div>
          )}
          {event.raw_output && (
            <CollapsiblePre title="Raw Test Output" content={event.raw_output} />
          )}
        </div>
      )}

      {type === 'files_needed' && event.files && (
        <div className="event-extra">
          <div className="file-list">
            {event.files.map((f, i) => (
              <code key={i} className="file-chip">{f}</code>
            ))}
          </div>
        </div>
      )}

      {type === 'file_contents' && event.files && (
        <div className="event-extra">
          {Object.entries(event.files).map(([path, content]) => (
            <CollapsiblePre key={path} title={path} content={content} />
          ))}
        </div>
      )}

      {type === 'fixes' && event.fixes && (
        <div className="event-extra">
          <div className="mini-fixes">
            {event.fixes.map((fix, i) => (
              <div key={i} className="mini-fix">
                <span className={`bug-badge ${fix.bug_type}`}>{fix.bug_type}</span>
                <code className="fix-file">{fix.file}:{fix.line}</code>
                <span className="fix-desc">{fix.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {type === 'fix_applied' && (
        <div className="event-extra">
          <div className="event-stats">
            <span className="stat stat-pass">✓ {event.applied} applied</span>
            <span className="stat stat-fail">✗ {event.failed} failed</span>
          </div>
          {event.details && (
            <div className="mini-fixes">
              {event.details.map((d, i) => (
                <div key={i} className={`mini-fix ${d.status === 'applied' ? 'fix-ok' : 'fix-fail'}`}>
                  <span className="fix-status">{d.status === 'applied' ? '✓' : '✗'}</span>
                  <code className="fix-file">{d.file}:{d.line}</code>
                  <span className="fix-desc">{d.status_message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {type === 'commit' && (
        <div className="event-extra">
          <div className="event-detail">
            <span className="detail-label">Hash:</span>{' '}
            <code className="detail-code">{event.commit_hash}</code>
          </div>
          <div className="event-detail">
            <span className="detail-label">Branch:</span>{' '}
            <span className="detail-value">{event.branch}</span>
          </div>
          <div className="event-detail">
            <span className="detail-label">Push:</span>{' '}
            <span className={event.push_success ? 'stat-pass' : 'stat-fail'}>
              {event.push_success ? '✓ Success' : '✗ Failed'}
            </span>
          </div>
        </div>
      )}

      {type === 'done' && (
        <div className="event-extra">
          <div className="event-stats">
            <span className="stat">{event.total_iterations} iterations</span>
            <span className="stat">{event.total_failures_detected} failures found</span>
            <span className="stat">{event.total_fixes_applied} fixes applied</span>
            <span className="stat">{event.time_taken}s total</span>
          </div>
          <div className="event-detail">
            <span className="detail-label">Final Status:</span>{' '}
            <span className={`badge ${event.final_status === 'PASSED' ? 'passed' : 'failed'}`}>
              {event.final_status}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}


/* ========== COLLAPSIBLE PRE ========== */
function CollapsiblePre({ title, content }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="collapsible">
      <div className="collapsible-header" onClick={() => setExpanded(!expanded)}>
        <span>{expanded ? '▼' : '▶'} {title}</span>
      </div>
      {expanded && (
        <pre className="collapsible-pre">{content}</pre>
      )}
    </div>
  )
}


/* ========== SUMMARY CARD ========== */
function SummaryCard({ result }) {
  if (!result) return null
  const statusClass = result.final_status === 'PASSED' ? 'passed' :
    result.final_status === 'RUNNING' ? 'running' : 'failed'

  return (
    <section className="card summary-card" id="run-summary">
      <div className="card-header">
        <span className="card-icon">📊</span>
        <h2>Run Summary</h2>
      </div>
      <div className="summary-grid">
        <div className="summary-item">
          <div className="summary-label">Repository</div>
          <div className="summary-value mono small">{result.repo_url}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Team</div>
          <div className="summary-value">{result.team_name}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Leader</div>
          <div className="summary-value">{result.leader_name}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Branch</div>
          <div className="summary-value mono small">{result.branch_name}</div>
        </div>
        <div className="summary-item highlight-item">
          <div className="summary-label">Failures Detected</div>
          <div className="summary-value big">{result.total_failures_detected}</div>
        </div>
        <div className="summary-item highlight-item">
          <div className="summary-label">Fixes Applied</div>
          <div className="summary-value big">{result.total_fixes_applied}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">CI/CD Status</div>
          <div className="summary-value">
            <span className={`badge ${statusClass}`}>
              {result.final_status === 'PASSED' ? '✓' : result.final_status === 'RUNNING' ? '⟳' : '✗'}
              {' '}{result.final_status}
            </span>
          </div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Time Taken</div>
          <div className="summary-value mono">{result.time_taken}s</div>
        </div>
      </div>
    </section>
  )
}


/* ========== SCORE BREAKDOWN PANEL ========== */
function ScoreBreakdownPanel({ result }) {
  if (!result) return null

  const baseScore = 100
  const timeTaken = parseFloat(result.time_taken) || 0
  const speedBonus = timeTaken < 300 ? 10 : 0 // < 5 minutes
  const totalCommits = result.total_commits || result.all_fixes?.length || 0
  const efficiencyPenalty = totalCommits > 20 ? (totalCommits - 20) * 2 : 0
  const totalScore = Math.max(0, baseScore + speedBonus - efficiencyPenalty)

  const scoreItems = [
    { label: 'Base Score', value: baseScore, color: 'var(--accent)' },
    { label: 'Speed Bonus', value: speedBonus > 0 ? `+${speedBonus}` : '0', color: 'var(--success)', note: timeTaken < 300 ? '< 5 min ✓' : '≥ 5 min' },
    { label: 'Efficiency Penalty', value: efficiencyPenalty > 0 ? `-${efficiencyPenalty}` : '0', color: 'var(--error)', note: `${totalCommits} commits` },
  ]

  const scorePercent = Math.min(100, (totalScore / 110) * 100)

  return (
    <section className="card score-panel" id="score-breakdown">
      <div className="card-header">
        <span className="card-icon">🏆</span>
        <h2>Score Breakdown</h2>
      </div>

      <div className="score-display">
        <div className="score-circle">
          <svg viewBox="0 0 120 120" className="score-ring">
            <circle cx="60" cy="60" r="52" className="ring-bg" />
            <circle
              cx="60" cy="60" r="52"
              className="ring-fill"
              style={{
                strokeDasharray: `${scorePercent * 3.27} 327`,
              }}
            />
          </svg>
          <div className="score-number">{totalScore}</div>
          <div className="score-label">Total Score</div>
        </div>
      </div>

      <div className="score-breakdown-bars">
        {scoreItems.map((item, i) => (
          <div key={i} className="score-row">
            <div className="score-row-label">
              <span>{item.label}</span>
              {item.note && <span className="score-note">{item.note}</span>}
            </div>
            <div className="score-row-bar">
              <div
                className="score-bar-fill"
                style={{
                  width: `${Math.abs(parseInt(item.value)) / 110 * 100}%`,
                  backgroundColor: item.color,
                }}
              />
            </div>
            <div className="score-row-value" style={{ color: item.color }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}


/* ========== CI/CD STATUS TIMELINE ========== */
function CICDTimeline({ runs, retryLimit = 5 }) {
  return (
    <section className="card timeline-section" id="cicd-timeline">
      <div className="card-header">
        <span className="card-icon">🔄</span>
        <h2>CI/CD Status Timeline</h2>
        <span className="iteration-count">{runs.length}/{retryLimit} iterations</span>
      </div>
      <div className="timeline">
        {runs.map((run, i) => (
          <div key={i} className={`timeline-item ${run.status}`}>
            <div className="timeline-marker">
              <div className={`marker-dot ${run.status}`}>
                {run.status === 'passed' ? '✓' : run.status === 'running' ? '⟳' : '✗'}
              </div>
              {i < runs.length - 1 && <div className="marker-line" />}
            </div>
            <div className="timeline-content">
              <div className="timeline-head">
                <span className="iter-title">Iteration {run.iteration || i + 1}</span>
                <span className={`badge small ${run.status}`}>
                  {run.status === 'passed' ? 'PASSED' : run.status === 'running' ? 'RUNNING' : 'FAILED'}
                </span>
              </div>
              <div className="timeline-details">
                <span className="iter-time">🕐 {run.timestamp}</span>
                {run.passed !== undefined && (
                  <span className="stat-pass">✅ {run.passed} passed</span>
                )}
                {run.failed !== undefined && run.failed > 0 && (
                  <span className="stat-fail">❌ {run.failed} failed</span>
                )}
                {run.fixes_applied !== undefined && (
                  <span className="stat-info">🔧 {run.fixes_applied} fixes</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}


/* ========== FIXES TABLE ========== */
function FixesTable({ fixes }) {
  return (
    <section className="card fixes-section" id="fixes-table">
      <div className="card-header">
        <span className="card-icon">🔨</span>
        <h2>All Fixes Applied</h2>
        <span className="fixes-count">{fixes.length} fixes</span>
      </div>
      <div className="fixes-table-wrapper">
        <table className="fixes-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Bug Type</th>
              <th>Line</th>
              <th>Commit Message</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {fixes.map((fix, i) => (
              <tr key={i}>
                <td className="file-name">{fix.file}</td>
                <td>
                  <span className={`bug-badge ${fix.bug_type}`}>
                    {fix.bug_type}
                  </span>
                </td>
                <td className="line-num">{fix.line}</td>
                <td className="commit-msg">{fix.commit_message || fix.description || `[AI-AGENT] Fix ${fix.bug_type} in ${fix.file}`}</td>
                <td>
                  <span className={`status-badge ${fix.status === 'applied' ? 'success' : 'fail'}`}>
                    {fix.status === 'applied' ? '✓ Fixed' : '✗ Failed'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}


export default App
