import { useState, useEffect, useRef } from 'react'
import './index.css'

const API_BASE = 'http://localhost:5000'

function App() {
  const [repoUrl, setRepoUrl] = useState('https://github.com/Code71590/buggy-calculator')
  const [teamName, setTeamName] = useState('')
  const [leaderName, setLeaderName] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [events, setEvents] = useState([])         // Live SSE events
  const [finalResult, setFinalResult] = useState(null)
  const eventSourceRef = useRef(null)
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

        // Update status message from step events
        if (data.message) {
          setStatusMessage(data.message)
        }

        // Append event to live feed
        setEvents(prev => [...prev, { ...data, _ts: new Date().toLocaleTimeString() }])

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
      // SSE connection lost — check if pipeline is still running
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

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="logo">⚡</div>
        <h1>CI/CD Healing Agent</h1>
        <span className="subtitle">Autonomous DevOps Agent</span>
      </header>

      <main className="main-content">
        {/* Input Section */}
        <InputForm
          repoUrl={repoUrl}
          setRepoUrl={setRepoUrl}
          teamName={teamName}
          setTeamName={setTeamName}
          leaderName={leaderName}
          setLeaderName={setLeaderName}
          isRunning={isRunning}
          onRun={handleRun}
        />

        {/* Status Bar */}
        {isRunning && (
          <div className="status-bar">
            <div className="pulse" />
            <span className="message">{statusMessage}</span>
          </div>
        )}

        {/* Live Event Feed — appears progressively */}
        {events.length > 0 && (
          <div className="live-feed">
            <h2 className="live-feed-title">
              <span className="live-dot" />
              {isRunning ? 'Live Pipeline Feed' : 'Pipeline Run Complete'}
            </h2>
            <div className="event-list">
              {events.map((evt, i) => (
                <EventCard key={i} event={evt} />
              ))}
              <div ref={eventsEndRef} />
            </div>
          </div>
        )}

        {/* Final Summary after done */}
        {finalResult && (
          <>
            <SummaryCard result={finalResult.result || finalResult} />
            {finalResult.result?.all_fixes?.length > 0 && (
              <FixesTable fixes={finalResult.result.all_fixes} />
            )}
          </>
        )}
      </main>
    </div>
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
                <span className={`bug-type ${fix.bug_type}`}>{fix.bug_type}</span>
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


/* ========== INPUT FORM ========== */
function InputForm({ repoUrl, setRepoUrl, teamName, setTeamName, leaderName, setLeaderName, isRunning, onRun }) {
  return (
    <section className="input-section">
      <h2><span className="icon">🔧</span> Configure Agent</h2>
      <div className="form-grid">
        <div className="form-group full-width">
          <label>GitHub Repository URL</label>
          <input
            type="text"
            placeholder="https://github.com/user/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            disabled={isRunning}
          />
        </div>
        <div className="form-group">
          <label>Team Name</label>
          <input
            type="text"
            placeholder="e.g., RIFT ORGANISERS"
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            disabled={isRunning}
          />
        </div>
        <div className="form-group">
          <label>Team Leader Name</label>
          <input
            type="text"
            placeholder="e.g., Saiyam Kumar"
            value={leaderName}
            onChange={(e) => setLeaderName(e.target.value)}
            disabled={isRunning}
          />
        </div>
        <div className="form-group">
          <label>&nbsp;</label>
          <button className="btn-run" onClick={onRun} disabled={isRunning}>
            {isRunning ? (
              <>
                <span className="spinner" />
                Agent Running...
              </>
            ) : (
              <>🚀 Run Agent</>
            )}
          </button>
        </div>
      </div>
    </section>
  )
}


/* ========== SUMMARY CARD ========== */
function SummaryCard({ result }) {
  if (!result) return null
  const statusClass = result.final_status === 'PASSED' ? 'passed' :
    result.final_status === 'RUNNING' ? 'running' : 'failed'

  return (
    <section className="summary-card">
      <h2>📊 Run Summary</h2>
      <div className="summary-grid">
        <div className="summary-item">
          <div className="label">Repository</div>
          <div className="value small">{result.repo_url}</div>
        </div>
        <div className="summary-item">
          <div className="label">Team</div>
          <div className="value">{result.team_name}</div>
        </div>
        <div className="summary-item">
          <div className="label">Leader</div>
          <div className="value">{result.leader_name}</div>
        </div>
        <div className="summary-item">
          <div className="label">Branch</div>
          <div className="value small">{result.branch_name}</div>
        </div>
        <div className="summary-item">
          <div className="label">Failures Detected</div>
          <div className="value">{result.total_failures_detected}</div>
        </div>
        <div className="summary-item">
          <div className="label">Fixes Applied</div>
          <div className="value">{result.total_fixes_applied}</div>
        </div>
        <div className="summary-item">
          <div className="label">Status</div>
          <div className="value">
            <span className={`badge ${statusClass}`}>
              {result.final_status === 'PASSED' ? '✓' : result.final_status === 'RUNNING' ? '⟳' : '✗'}
              {' '}{result.final_status}
            </span>
          </div>
        </div>
        <div className="summary-item">
          <div className="label">Time Taken</div>
          <div className="value">{result.time_taken}s</div>
        </div>
      </div>
    </section>
  )
}


/* ========== FIXES TABLE ========== */
function FixesTable({ fixes }) {
  return (
    <section className="fixes-section">
      <h2>🔨 All Fixes Applied</h2>
      <div className="fixes-table-wrapper">
        <table className="fixes-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Bug Type</th>
              <th>Line</th>
              <th>Description</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {fixes.map((fix, i) => (
              <tr key={i}>
                <td className="file-name">{fix.file}</td>
                <td>
                  <span className={`bug-type ${fix.bug_type}`}>
                    {fix.bug_type}
                  </span>
                </td>
                <td>{fix.line}</td>
                <td>{fix.description}</td>
                <td>
                  <span className={`status-icon ${fix.status === 'applied' ? 'success' : 'fail'}`}>
                    {fix.status === 'applied' ? '✓' : '✗'}
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
