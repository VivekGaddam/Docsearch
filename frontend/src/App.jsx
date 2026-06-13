import { useEffect, useRef, useState } from 'react';
import {
  createWorkspace,
  fetchConnectors,
  fetchDocuments,
  fetchReports,
  fetchWorkspaces,
  login,
  register,
  runResearch,
  searchWorkspace,
  uploadDocument,
} from './services/api';
import './App.css';

const SUGGESTIONS = [
  'Summarize the key points in my documents',
  'Compare the documents in my workspace',
  'Extract all key entities and facts',
  'What are the main findings?',
];

// Intent metadata
const INTENT_META = {
  summarize:  { emoji: '📝', label: 'Summarize' },
  compare:    { emoji: '⚖️', label: 'Compare' },
  extract:    { emoji: '🔍', label: 'Extract' },
  research:   { emoji: '🔬', label: 'Research' },
  explain:    { emoji: '💡', label: 'Explain' },
  qa:         { emoji: '❓', label: 'Q&A' },
  general:    { emoji: '💬', label: 'General' },
  greeting:   { emoji: '👋', label: 'Chat' },
};

const MCP_TOOL_ICONS = {
  search_workspace: '🔎',
  classify_intent: '🧠',
  synthesize_answer: '⚡',
  compare_documents: '⚖️',
  github: '🐙',
  google_drive: '📁',
  notion: '📔',
  slack: '💬',
  confluence: '🏔️',
};

function simpleMarkdown(text) {
  if (!text) return null;
  return text.split('\n').map((line, i) => {
    if (line.startsWith('### ')) return <h4 key={i}>{line.slice(4)}</h4>;
    if (line.startsWith('## ')) return <h3 key={i}>{line.slice(3)}</h3>;
    if (line.startsWith('# ')) return <h3 key={i}>{line.slice(2)}</h3>;
    if (line.startsWith('- ')) return <li key={i}>{line.slice(2)}</li>;
    if (!line.trim()) return <br key={i} />;
    return <p key={i}>{line}</p>;
  });
}

function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ fullName: '', email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res =
        mode === 'register'
          ? await register(form)
          : await login({ email: form.email, password: form.password });
      localStorage.setItem('token', res.access_token);
      onAuth(res.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon">DS</div>
          <span>DocSearch</span>
        </div>
        <h1>{mode === 'register' ? 'Create account' : 'Welcome back'}</h1>
        <p>Research across your documents with cited answers.</p>

        <div className="auth-tabs">
          <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>
            Sign in
          </button>
          <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="auth-field">
              <label>Full name</label>
              <input
                value={form.fullName}
                onChange={(e) => setForm({ ...form, fullName: e.target.value })}
                placeholder="Jane Doe"
                required
              />
            </div>
          )}
          <div className="auth-field">
            <label>Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="you@company.com"
              required
            />
          </div>
          <div className="auth-field">
            <label>Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="••••••••"
              required
            />
          </div>
          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'}
          </button>
        </form>
        {error && <p className="auth-error">{error}</p>}
      </div>
    </div>
  );
}

// ── Intent + Confidence display (inline in message) ──────────────────────────
function IntentMeta({ intent, confidence, subQueries, evidenceGaps }) {
  const [showChain, setShowChain] = useState(false);
  const meta = INTENT_META[intent] || INTENT_META.general;
  const pct = Math.round((confidence || 0) * 100);

  return (
    <div style={{ marginTop: 12 }}>
      <div className="intent-row">
        <span className={`intent-badge ${intent}`}>
          {meta.emoji} {meta.label}
        </span>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>Confidence</span>
        <div className="confidence-bar" style={{ width: 80, display: 'inline-block' }}>
          <div className="confidence-fill" style={{ width: `${pct}%` }} />
        </div>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>{pct}%</span>
      </div>

      {subQueries && subQueries.length > 1 && (
        <div className="sub-queries">
          {subQueries.map((q, i) => (
            <span key={i} className="sub-query-chip" title={q}>{q}</span>
          ))}
        </div>
      )}

      {evidenceGaps && evidenceGaps.length > 0 && (
        <div className="evidence-gaps">
          <div className="evidence-gaps-title">⚠ Evidence gaps</div>
          {evidenceGaps.map((g, i) => (
            <div key={i} className="evidence-gap-item">{g}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Inline reasoning chain toggle ─────────────────────────────────────────────
function ReasoningChainInline({ chain }) {
  const [open, setOpen] = useState(false);
  if (!chain || chain.length === 0) return null;

  return (
    <div className="reasoning-section">
      <button
        className={`reasoning-toggle ${open ? 'open' : ''}`}
        onClick={() => setOpen(v => !v)}
        type="button"
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
          <polygon points="2,1 8,5 2,9" />
        </svg>
        {chain.length}-step reasoning chain
      </button>
      {open && (
        <div className="reasoning-chain">
          {chain.map((step, i) => (
            <div key={i} className="reasoning-step">
              <div className="reasoning-step-name">{step.step}</div>
              <div className="reasoning-step-thought">💭 {step.thought}</div>
              <div className="reasoning-step-conclusion">→ {step.conclusion}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWs, setActiveWs] = useState('');
  const [documents, setDocuments] = useState([]);
  const [reports, setReports] = useState([]);
  const [connectors, setConnectors] = useState([]);
  const [wsName, setWsName] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('search');
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(false);
  const [toast, setToast] = useState('');
  const [contextTab, setContextTab] = useState('sources');
  const [activeContext, setActiveContext] = useState(null);
  const bottomRef = useRef(null);

  const workspace = workspaces.find((w) => w.id === activeWs);

  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  }

  useEffect(() => {
    const onLogout = () => setToken('');
    window.addEventListener('auth:logout', onLogout);
    return () => window.removeEventListener('auth:logout', onLogout);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      setBooting(true);
      try {
        const [ws, conn] = await Promise.all([fetchWorkspaces(), fetchConnectors()]);
        if (cancelled) return;
        setWorkspaces(ws);
        setConnectors(conn);
        if (ws.length) {
          setActiveWs(ws[0].id);
          const [docs, reps] = await Promise.all([
            fetchDocuments(ws[0].id),
            fetchReports(ws[0].id),
          ]);
          if (!cancelled) {
            setDocuments(docs);
            setReports(reps);
          }
        }
      } catch (err) {
        if (!cancelled) showToast(err.message || 'Failed to load workspace');
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  async function loadWorkspaceData(wsId) {
    const [docs, reps] = await Promise.all([fetchDocuments(wsId), fetchReports(wsId)]);
    setDocuments(docs);
    setReports(reps);
  }

  async function switchWorkspace(wsId) {
    setActiveWs(wsId);
    setMessages([]);
    setActiveContext(null);
    try {
      await loadWorkspaceData(wsId);
    } catch (err) {
      showToast(err.message);
    }
  }

  async function handleCreateWs() {
    if (!wsName.trim()) {
      showToast('Enter a workspace name');
      return;
    }
    setLoading(true);
    try {
      const ws = await createWorkspace({ name: wsName.trim(), description: '' });
      setWorkspaces((prev) => [ws, ...prev]);
      setWsName('');
      setActiveWs(ws.id);
      setDocuments([]);
      setReports([]);
      setMessages([]);
      showToast(`Workspace "${ws.name}" created`);
    } catch (err) {
      showToast(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!activeWs) {
      showToast('Create a workspace first');
      e.target.value = '';
      return;
    }
    setLoading(true);
    try {
      const res = await uploadDocument(activeWs, file);
      setDocuments(await fetchDocuments(activeWs));
      showToast(`Uploaded ${res.document.filename} (${res.ingested_chunks} chunks)`);
    } catch (err) {
      showToast(err.message);
    } finally {
      e.target.value = '';
      setLoading(false);
    }
  }

  async function handleSend(text) {
    const query = (text || input).trim();
    if (!query || loading) return;
    if (!activeWs) {
      showToast('Create a workspace first — type a name on the left and click +');
      return;
    }

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setLoading(true);
    setActiveContext(null);

    try {
      if (mode === 'research') {
        const result = await runResearch({
          workspace_id: activeWs,
          query,
          session_title: query.slice(0, 60),
        });
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: result.report_markdown,
            type: 'research',
            citations: result.citations,
            plan: null,
          },
        ]);
        setActiveContext({
          citations: result.citations,
          plan: null,
          steps: [],
          mode: 'research',
        });
        setReports(await fetchReports(activeWs));
      } else {
        const result = await searchWorkspace({
          workspace_id: activeWs,
          query,
          top_k: 5,
          include_web: true,
        });
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: result.answer,
            type: 'search',
            citations: result.citations,
            plan: result.plan,
            // ── New reasoning/intent fields ──
            intent: result.intent || 'general',
            task_type: result.task_type || 'general',
            confidence: result.confidence ?? 1.0,
            reasoning_chain: result.reasoning_chain || [],
            evidence_gaps: result.evidence_gaps || [],
            sub_queries: result.sub_queries || [],
          },
        ]);
        setActiveContext({
          citations: result.citations,
          plan: result.plan,
          steps: result.steps || [],
          mode: result.mode || 'rag',
          intent: result.intent || 'general',
          confidence: result.confidence ?? 1.0,
          reasoning_chain: result.reasoning_chain || [],
          evidence_gaps: result.evidence_gaps || [],
          sub_queries: result.sub_queries || [],
        });
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}`, type: 'error' },
      ]);
      showToast(err.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem('token');
    setToken('');
    setWorkspaces([]);
    setMessages([]);
  }

  if (!token) {
    return <AuthPage onAuth={setToken} />;
  }

  const citations = activeContext?.citations || [];
  const plan = activeContext?.plan || [];
  const agentSteps = activeContext?.steps || [];
  const reasoningChain = activeContext?.reasoning_chain || [];
  const evidenceGaps = activeContext?.evidence_gaps || [];

  return (
    <div className="app-shell">
      {toast && <div className="toast error">{toast}</div>}

      {/* LEFT — workspaces + docs */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">DS</div>
          <div>
            <div className="sidebar-title">DocSearch</div>
            <div className="sidebar-sub">{documents.length} sources · {reports.length} reports</div>
          </div>
        </div>

        <div className="sidebar-section">Workspaces</div>
        <div className="new-workspace">
          <input
            value={wsName}
            onChange={(e) => setWsName(e.target.value)}
            placeholder="New workspace"
            onKeyDown={(e) => e.key === 'Enter' && handleCreateWs()}
          />
          <button type="button" onClick={handleCreateWs}>+</button>
        </div>
        <div className="sidebar-list">
          {workspaces.map((ws) => (
            <button
              key={ws.id}
              type="button"
              className={`sidebar-item ${ws.id === activeWs ? 'active' : ''}`}
              onClick={() => switchWorkspace(ws.id)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
              </svg>
              <div className="sidebar-item-info">
                <strong>{ws.name}</strong>
              </div>
            </button>
          ))}
        </div>

        <div className="sidebar-section">Sources</div>
        <div className="sidebar-list">
          {documents.length === 0 ? (
            <p style={{ padding: '8px 16px', fontSize: 12, color: 'var(--muted)' }}>No documents yet</p>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="doc-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" />
                </svg>
                <span>{doc.filename}</span>
                <span className={`doc-status ${doc.status}`}>{doc.status}</span>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <label className="sidebar-action upload">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload document
            <input type="file" accept=".pdf,.docx,.pptx,.txt,.md,.csv" onChange={handleUpload} />
          </label>
          <button type="button" className="sidebar-action" onClick={logout}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* CENTER — chat */}
      <main className="chat-panel">
        <div className="chat-header">
          <div>
            <h2>{booting ? 'Loading…' : workspace?.name || 'No workspace'}</h2>
            <span>{mode === 'research' ? 'Deep research mode' : 'Intelligent search & reasoning'}</span>
          </div>
        </div>

        {!activeWs && !booting && (
          <div className="no-workspace-banner">
            <strong>No workspace yet</strong>
            Type a name in the sidebar (e.g. &quot;My Research&quot;) and click + to create one, then upload documents and start asking questions.
          </div>
        )}

        <div className="chat-messages">
          {messages.length === 0 && !loading && (
            <div className="chat-empty">
              <div className="chat-empty-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                </svg>
              </div>
              <h3>Ask anything about your documents</h3>
              <p>Upload sources on the left. The AI classifies your intent, routes to a specialist agent, reasons over evidence, and delivers a cited answer.</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} type="button" className="suggestion" onClick={() => handleSend(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`msg ${msg.role}`}>
              <div className="msg-avatar">{msg.role === 'user' ? 'You' : 'AI'}</div>
              <div className="msg-body">
                {msg.role === 'user' ? (
                  msg.content
                ) : (
                  <>
                    {simpleMarkdown(msg.content)}
                    {msg.type && msg.type !== 'error' && (
                      <>
                        <div className="msg-meta">
                          <span className={`msg-badge ${msg.type}`}>
                            {msg.type === 'research' ? 'Deep research' : 'Search'}
                          </span>
                          {msg.citations?.length > 0 && (
                            <span className="msg-badge search">{msg.citations.length} sources</span>
                          )}
                        </div>

                        {/* Intent + Confidence + Gaps (only for search mode) */}
                        {msg.type === 'search' && msg.intent && (
                          <IntentMeta
                            intent={msg.intent}
                            confidence={msg.confidence}
                            subQueries={msg.sub_queries}
                            evidenceGaps={msg.evidence_gaps}
                          />
                        )}

                        {/* Inline reasoning chain toggle */}
                        {msg.type === 'search' && msg.reasoning_chain?.length > 0 && (
                          <ReasoningChainInline chain={msg.reasoning_chain} />
                        )}
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="msg assistant">
              <div className="msg-avatar">AI</div>
              <div className="msg-loading">
                <div className="dots"><span /><span /><span /></div>
                {mode === 'research' ? 'Running deep research…' : 'Classifying intent & reasoning…'}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-composer">
          <div className="composer-box">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={mode === 'research' ? 'Ask for a detailed research report…' : 'Ask a question — intent will be classified automatically…'}
              disabled={loading || booting}
            />
            <div className="composer-actions">
              <div className="composer-modes">
                <button
                  type="button"
                  className={`mode-btn ${mode === 'search' ? 'active' : ''}`}
                  onClick={() => setMode('search')}
                >
                  🧠 Smart search
                </button>
                <button
                  type="button"
                  className={`mode-btn ${mode === 'research' ? 'active' : ''}`}
                  onClick={() => setMode('research')}
                >
                  🔬 Deep research
                </button>
              </div>
              <div className="composer-send">
                <button
                  type="button"
                  className="send-btn primary"
                  onClick={() => handleSend()}
                  disabled={!input.trim() || loading || booting}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* RIGHT — context panel */}
      <aside className="context-panel">
        <div className="context-header">Intelligence Panel</div>
        <div className="context-tabs">
          <button type="button" className={contextTab === 'sources' ? 'active' : ''} onClick={() => setContextTab('sources')}>
            Sources ({citations.length})
          </button>
          <button type="button" className={contextTab === 'reasoning' ? 'active' : ''} onClick={() => setContextTab('reasoning')}>
            Reasoning
          </button>
          <button type="button" className={contextTab === 'mcp' ? 'active' : ''} onClick={() => setContextTab('mcp')}>
            MCP
          </button>
        </div>

        <div className="context-body">
          {/* ── Sources tab ── */}
          {contextTab === 'sources' && (
            citations.length === 0 ? (
              <p className="context-empty">Sources used in the latest answer will appear here.</p>
            ) : (
              citations.map((c, i) => (
                <div key={i} className="source-card">
                  <div className="source-card-top">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      {c.source_type === 'web' ? (
                        <>
                          <circle cx="12" cy="12" r="10" />
                          <line x1="2" y1="12" x2="22" y2="12" />
                          <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
                        </>
                      ) : (
                        <>
                          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                        </>
                      )}
                    </svg>
                    <strong>{c.document_name}</strong>
                    <span className="source-type">{c.source_type}</span>
                  </div>
                  {c.page_number && <span>Page {c.page_number}</span>}
                  {c.url && <span>{c.url}</span>}
                </div>
              ))
            )
          )}

          {/* ── Reasoning tab ── */}
          {contextTab === 'reasoning' && (
            <>
              {/* Intent + confidence summary */}
              {activeContext?.intent && activeContext.intent !== 'general' && (
                <div style={{ marginBottom: 12 }}>
                  <div className="intent-row">
                    <span className={`intent-badge ${activeContext.intent}`}>
                      {INTENT_META[activeContext.intent]?.emoji} {INTENT_META[activeContext.intent]?.label}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                      {Math.round((activeContext.confidence || 0) * 100)}% confidence
                    </span>
                  </div>
                  <div className="confidence-bar-wrap">
                    <span>Confidence</span>
                    <div className="confidence-bar">
                      <div className="confidence-fill" style={{ width: `${Math.round((activeContext.confidence || 0) * 100)}%` }} />
                    </div>
                    <span>{Math.round((activeContext.confidence || 0) * 100)}%</span>
                  </div>
                </div>
              )}

              {/* Reasoning chain cards */}
              {reasoningChain.length > 0 ? (
                <>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--purple)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Reasoning Chain
                  </div>
                  {reasoningChain.map((step, i) => (
                    <div key={i} className="chain-step-card">
                      <div className="chain-step-header">
                        <div className="chain-step-dot" />
                        <div className="chain-step-name">{i + 1}. {step.step}</div>
                      </div>
                      <div className="chain-step-thought">💭 {step.thought}</div>
                      <div className="chain-step-conclusion">→ {step.conclusion}</div>
                    </div>
                  ))}
                </>
              ) : agentSteps.length > 0 ? (
                <>
                  <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--purple)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Agent Steps
                  </div>
                  {agentSteps.map((step, i) => (
                    <div key={i} className="plan-step">
                      <div className="plan-num">{i + 1}</div>
                      <div>
                        <strong style={{ display: 'block', fontSize: 12, marginBottom: 2 }}>{step.label}</strong>
                        <span>{step.summary}</span>
                      </div>
                    </div>
                  ))}
                </>
              ) : plan.length > 0 ? (
                plan.map((step, i) => (
                  <div key={i} className="plan-step">
                    <div className="plan-num">{i + 1}</div>
                    <span>{step}</span>
                  </div>
                ))
              ) : (
                <p className="context-empty">Reasoning steps appear after a search.</p>
              )}

              {/* Evidence gaps */}
              {evidenceGaps.length > 0 && (
                <div className="evidence-gaps" style={{ marginTop: 12 }}>
                  <div className="evidence-gaps-title">⚠ Evidence gaps detected</div>
                  {evidenceGaps.map((g, i) => (
                    <div key={i} className="evidence-gap-item">{g}</div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* ── MCP tab ── */}
          {contextTab === 'mcp' && (
            <>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--purple)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8, padding: '0 2px' }}>
                MCP Tools — /mcp/v1
              </div>
              {connectors.length === 0 ? (
                <p className="context-empty">Loading MCP connectors…</p>
              ) : (
                connectors.map((c, i) => (
                  <div key={i} className="mcp-tool-card">
                    <div className="mcp-tool-header">
                      <div className="mcp-tool-icon">{MCP_TOOL_ICONS[c.name] || '🔌'}</div>
                      <div className="mcp-tool-name">{c.name}</div>
                      <span className={`mcp-tool-status ${c.status}`}>{c.status}</span>
                    </div>
                    <div className="mcp-tool-caps">
                      {(c.capabilities || []).map((cap, j) => (
                        <span key={j} className="mcp-cap">{cap.replace(/_/g, ' ')}</span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

export default App;
