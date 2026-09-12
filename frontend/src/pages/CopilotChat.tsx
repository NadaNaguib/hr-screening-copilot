import React, { useState, useEffect, useRef } from "react"
import {
  Send,
  Loader2,
  Plus,
  Trash2,
  MessageSquare,
  Sparkles,
  BookOpen,
  FileText,
  ChevronRight,
  User,
  Bot,
  Search,
  Check,
  ArrowLeft,
  ArrowRight,
  Eye,
  Copy,
  X,
  ExternalLink,
  ShieldAlert,
} from "lucide-react"
import { createSSEConnection, SSEStatus } from "../lib/sse"
import { CvViewerModal } from "../components/CvViewerModal"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1"

export interface Citation {
  id?: string
  quote: string
  source: string
  page: number | null
  candidate_id?: string
  chunk_id?: string
  full_context?: string
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
  timestamp: string
  /** Which RAG mode produced this answer (drives the degraded banner). */
  mode?: "agentic" | "plain_rag"
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  updatedAt: string
}

const STORAGE_KEY = "hr_copilot_saved_sessions"

const SAMPLE_PROMPTS = [
  "What Python frameworks does Alice Johnson know?",
  "Compare top candidates for the Senior Backend Engineer position.",
  "Which candidates have demonstrated Docker and Kubernetes experience?",
  "Summarize key evidence extracted for microservices and cloud architecture.",
]

export function CopilotChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string>("")
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [, setStatus] = useState<SSEStatus>("closed")

  // Modal / Document Inspector State
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [activeCitations, setActiveCitations] = useState<Citation[]>([])
  const [activeCitationIndex, setActiveCitationIndex] = useState<number>(0)
  const [copied, setCopied] = useState(false)
  const [searchFilter, setSearchFilter] = useState("")
  const [selectedCvCandidate, setSelectedCvCandidate] = useState<{ id: string; name?: string } | null>(null)

  const [agentTrace, setAgentTrace] = useState<{agent: string, status: string}[]>([])
  const [activeStatus, setActiveStatus] = useState<string>("")

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const highlightRef = useRef<HTMLDivElement | null>(null)
  const cancelStreamRef = useRef<(() => void) | null>(null)

  // Load saved sessions on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed: ChatSession[] = JSON.parse(saved)
        if (parsed && parsed.length > 0) {
          setSessions(parsed)
          setCurrentSessionId(parsed[0].id)
          return
        }
      }
    } catch {
      // ignore
    }
    // Start initial empty session
    startNewSession()
  }, [])

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    }
  }, [sessions])

  // Scroll to bottom on message updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [sessions, currentSessionId, loading])

  // Scroll to highlighted citation when modal opens or index changes
  useEffect(() => {
    if (inspectorOpen) {
      const timer = setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
      }, 150)
      return () => clearTimeout(timer)
    }
  }, [inspectorOpen, activeCitationIndex])

  const currentSession = sessions.find((s) => s.id === currentSessionId)
  const messages = currentSession?.messages || []

  function startNewSession() {
    if (loading && cancelStreamRef.current) {
      cancelStreamRef.current()
      setLoading(false)
    }
    const newSession: ChatSession = {
      id: "sess_" + Date.now(),
      title: "New Conversation",
      messages: [],
      updatedAt: new Date().toISOString(),
    }
    setSessions((prev) => [newSession, ...prev])
    setCurrentSessionId(newSession.id)
    setInspectorOpen(false)
  }

  function deleteSession(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    const remaining = sessions.filter((s) => s.id !== id)
    setSessions(remaining)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(remaining))
    if (currentSessionId === id) {
      if (remaining.length > 0) {
        setCurrentSessionId(remaining[0].id)
      } else {
        startNewSession()
      }
    }
  }

  function openInspector(citations: Citation[], index: number = 0) {
    if (!citations || citations.length === 0) return
    setActiveCitations(citations)
    setActiveCitationIndex(Math.max(0, Math.min(index, citations.length - 1)))
    setInspectorOpen(true)
    setCopied(false)
    setSearchFilter("")
  }

  function handleCopyQuote(quoteText: string) {
    const active = activeCitations[activeCitationIndex]
    const fullText = `"${quoteText}" — ${active?.source || "CV"} (Page ${active?.page ?? 1})`
    navigator.clipboard.writeText(fullText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleSend(textToSend?: string) {
    const questionText = (textToSend || input).trim()
    if (!questionText || loading) return

    const userMessage: ChatMessage = {
      id: "msg_" + Date.now(),
      role: "user",
      content: questionText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    }

    const assistantPlaceholderId = "msg_asst_" + (Date.now() + 1)
    const assistantMessage: ChatMessage = {
      id: assistantPlaceholderId,
      role: "assistant",
      content: "",
      citations: [],
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    }

    const updatedMessages = [...messages, userMessage, assistantMessage]
    const updatedTitle =
      currentSession?.title === "New Conversation"
        ? questionText.slice(0, 32) + (questionText.length > 32 ? "…" : "")
        : currentSession?.title || "Conversation"

    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId
          ? {
              ...s,
              title: updatedTitle,
              messages: updatedMessages,
              updatedAt: new Date().toISOString(),
            }
          : s
      )
    )

    setInput("")
    setLoading(true)
    setStatus("connecting")

    let accumulatedAnswer = ""
    let accumulatedCitations: Citation[] = []
    let responseMode: "agentic" | "plain_rag" = "agentic"
    setAgentTrace([])
    setActiveStatus("")

    // Patch the in-flight assistant message as tokens / status events arrive.
    const patchAssistant = (patch: Partial<ChatMessage>) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === currentSessionId
            ? {
                ...s,
                messages: s.messages.map((m) =>
                  m.id === assistantPlaceholderId ? { ...m, ...patch } : m
                ),
              }
            : s
        )
      )
    }

    const cleanup = createSSEConnection({
      url: `${API_BASE}/chat`,
      body: { question: questionText },
      onStatus: setStatus,
      onEvent: (event: any) => {
        if (event.type === "agent_event") {
          const evData = event.data || {}
          const agentName = evData.agent || ""
          const agentStatus = evData.status || "done"
          if (agentName) {
            setActiveStatus(
              agentStatus === "degraded" ? "Plain RAG (degraded)" : agentName.replace(/_/g, ' ')
            )
            setAgentTrace(prev => {
              const existing = prev.findIndex(t => t.agent === agentName)
              if (existing >= 0) {
                const updated = [...prev]
                updated[existing] = {agent: agentName, status: agentStatus}
                return updated
              }
              return [...prev, {agent: agentName, status: agentStatus}]
            })
          }
          // A "degraded" status means the answer is coming from the Plain RAG path.
          if (agentStatus === "degraded") {
            responseMode = "plain_rag"
            patchAssistant({ mode: "plain_rag" })
          }
        } else if (event.type === "answer_chunk") {
          const chunk = typeof event.data === "string" ? event.data : ""
          accumulatedAnswer += chunk

          const cites = event.citations || event.data?.citations
          if (Array.isArray(cites) && cites.length > 0) {
            accumulatedCitations = cites
          }

          patchAssistant({
            content: accumulatedAnswer,
            citations: accumulatedCitations,
            mode: responseMode,
          })
        } else if (event.type === "done" || event.event === "done") {
          if (event.data?.degraded) {
            responseMode = "plain_rag"
            patchAssistant({ mode: "plain_rag" })
          }
          setLoading(false)
          setStatus("closed")
          setActiveStatus("")
        }
      },
    })

    cancelStreamRef.current = () => {
      cleanup()
      setLoading(false)
      setStatus("closed")
    }
  }

  // Helper to render interactive markdown-like text with clickable citation links
  function renderInteractiveContent(content: string, citations?: Citation[]) {
    if (!content) return null

    // Match citations formatted as [1], [2], [1: file, Page 1], etc.
    const tokenRegex = /(\[\d+\]|\[\d+:[^\]]+\])/g
    const parts = content.split(tokenRegex)

    return (
      <div className="whitespace-pre-wrap leading-relaxed">
        {parts.map((part, i) => {
          const match = part.match(/\[(\d+)(?::\s*([^,\]]+))?\]?/)
          if (match && citations && citations.length > 0) {
            const index = parseInt(match[1], 10) - 1
            if (index >= 0 && index < citations.length) {
              const cite = citations[index]
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => openInspector(citations, index)}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 rounded-md bg-purple-100/80 hover:bg-purple-200 text-purple-900 border border-purple-300/80 font-mono text-[11px] font-semibold transition hover:scale-105 shadow-2xs cursor-pointer group align-baseline"
                  title={`Click to view citation in ${cite.source} (Page ${cite.page ?? 1})`}
                >
                  <FileText className="w-3 h-3 text-purple-600 group-hover:text-purple-800" />
                  <span>
                    [{index + 1}: {cite.source.replace(/\.[^/.]+$/, "")}#{cite.page ?? 1}]
                  </span>
                </button>
              )
            }
          }
          return <span key={i}>{part}</span>
        })}
      </div>
    )
  }

  const currentCitation = activeCitations[activeCitationIndex]

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] min-h-[550px] space-y-3">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-purple-600" /> HR Screening Copilot
          </h2>
        </div>
        <button
          onClick={startNewSession}
          className="px-3 py-1.5 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" /> New Chat
        </button>
      </div>

      {/* Main Chat Grid */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-4 overflow-hidden">
        {/* Left Sessions Sidebar */}
        <div className="hidden md:flex flex-col bg-white rounded-xl border border-surface-border shadow-xs overflow-hidden">
          <div className="p-3 border-b border-surface-border flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-surface-muted flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-brand-primary" /> Saved Conversations
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-mono">
              {sessions.length}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {sessions.map((sess) => {
              const isActive = sess.id === currentSessionId
              return (
                <div
                  key={sess.id}
                  onClick={() => setCurrentSessionId(sess.id)}
                  className={`group w-full text-left px-3 py-2.5 rounded-lg text-sm cursor-pointer flex items-center justify-between transition ${
                    isActive
                      ? "bg-purple-50 text-purple-950 font-medium border border-purple-200"
                      : "hover:bg-surface-page text-surface-text"
                  }`}
                >
                  <div className="truncate flex-1 mr-2">
                    <div className="truncate text-xs font-semibold">{sess.title}</div>
                    <div className="text-[10px] text-surface-muted font-mono">
                      {sess.messages.length} msgs
                    </div>
                  </div>
                  <button
                    onClick={(e) => deleteSession(sess.id, e)}
                    title="Delete chat session"
                    className="opacity-0 group-hover:opacity-100 text-surface-muted hover:text-red-600 transition p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        {/* Center & Right: Chat Area */}
        <div className="md:col-span-3 flex flex-col bg-white rounded-xl border border-surface-border shadow-xs overflow-hidden">
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
                  <Bot className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-surface-text">Welcome to your Talent Copilot</h3>
                  <p className="text-xs text-surface-muted max-w-md mt-1">
                    Ask questions about applicant competencies, compare qualifications against job rubrics, or click on citations to inspect exact CV excerpts.
                  </p>
                </div>

                <div className="w-full max-w-lg space-y-2 pt-2">
                  <div className="text-xs font-semibold text-surface-muted uppercase text-left">Suggested Questions:</div>
                  <div className="grid grid-cols-1 gap-2">
                    {SAMPLE_PROMPTS.map((prompt, i) => (
                      <button
                        key={i}
                        onClick={() => handleSend(prompt)}
                        className="text-left px-3.5 py-2 rounded-lg border border-surface-border hover:border-purple-300 hover:bg-purple-50/50 text-xs text-surface-text transition flex items-center justify-between group"
                      >
                        <span>{prompt}</span>
                        <ChevronRight className="w-3.5 h-3.5 text-surface-muted group-hover:text-purple-600 transition" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              messages.map((m) => {
                const isUser = m.role === "user"
                return (
                  <div
                    key={m.id}
                    className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    {/* Avatar */}
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                        isUser
                          ? "bg-brand-primary text-white"
                          : "bg-purple-600 text-white"
                      }`}
                    >
                      {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    {/* Bubble */}
                    <div
                      className={`max-w-[85%] rounded-2xl p-4 text-sm shadow-2xs ${
                        isUser
                          ? "bg-brand-primary text-white rounded-tr-xs"
                          : "bg-surface-page/70 text-surface-text border border-surface-border rounded-tl-xs"
                      }`}
                    >
                      <div>
                        {m.mode === "plain_rag" && (
                          <div className="mb-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">
                            <ShieldAlert className="w-3 h-3" /> Mode: Plain RAG (Degraded)
                          </div>
                        )}
                        {m.content ? (
                          renderInteractiveContent(m.content, m.citations)
                        ) : (
                          <div className="flex items-center gap-2 text-surface-muted text-xs italic">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            {m.mode === "plain_rag"
                              ? "Plain RAG (degraded) — retrieving context…"
                              : activeStatus
                              ? `Agentic RAG ▶ ${activeStatus}…`
                              : "Initializing agentic pipeline…"}
                          </div>
                        )}
                      </div>

                      {/* Interactive Grounded Citations Deck */}
                      {m.citations && m.citations.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-surface-border/60">
                          <div className="text-xs font-semibold text-purple-900 flex items-center justify-between mb-2">
                            <span className="flex items-center gap-1.5">
                              <BookOpen className="w-3.5 h-3.5 text-purple-600" />
                              {m.mode === "plain_rag" ? "Plain RAG Sources" : "Agentic RAG Sources"} ({m.citations.length})
                            </span>
                            <span className="text-[10px] text-surface-muted">
                              Multi-scope retrieval · Click to inspect
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {m.citations.map((cite, idx) => (
                              <div
                                key={idx}
                                onClick={() => openInspector(m.citations || [], idx)}
                                className="p-2.5 rounded-lg border border-purple-100 bg-white hover:bg-purple-50/80 hover:border-purple-300 transition cursor-pointer text-xs group flex flex-col justify-between"
                              >
                                <div>
                                  <div className="flex items-center justify-between text-purple-900 font-semibold mb-1">
                                    <span className="flex items-center gap-1 truncate max-w-[150px]" title={cite.source}>
                                      <FileText className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                                      <span className="truncate">[{idx + 1}] {cite.source}</span>
                                    </span>
                                    <span className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded font-mono shrink-0">
                                      Pg {cite.page ?? 1}
                                    </span>
                                  </div>
                                  {(cite as any).scope && (
                                    <span className={`inline-block text-[9px] px-1.5 py-0.5 rounded-full font-semibold mb-1 ${
                                      (cite as any).scope === 'candidate_cv' ? 'bg-blue-100 text-blue-700' :
                                      (cite as any).scope === 'talent_pool' ? 'bg-green-100 text-green-700' :
                                      (cite as any).scope === 'job_requirements' ? 'bg-orange-100 text-orange-700' :
                                      (cite as any).scope === 'rubric' ? 'bg-yellow-100 text-yellow-800' :
                                      (cite as any).scope === 'candidate_profile' ? 'bg-indigo-100 text-indigo-700' :
                                      'bg-gray-100 text-gray-600'
                                    }`}>
                                      🔍 {((cite as any).scope as string).replace(/_/g, ' ')}
                                    </span>
                                  )}
                                  <p className="text-surface-muted italic line-clamp-2 text-[11px]">
                                    &ldquo;{cite.quote}&rdquo;
                                  </p>
                                </div>
                                <div className="mt-2 pt-1.5 border-t border-purple-50 flex items-center justify-between text-[10px] text-purple-700 font-medium group-hover:text-purple-900">
                                  <span>Inspect source</span>
                                  <div className="flex items-center gap-1.5">
                                    {cite.candidate_id && (
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          setSelectedCvCandidate({
                                            id: cite.candidate_id!,
                                            name: cite.source.replace(/_CV\.(pdf|txt|docx)/i, "").replace(/_/g, " "),
                                          })
                                        }}
                                        className="px-1.5 py-0.5 bg-indigo-50 hover:bg-indigo-100 text-brand-primary border border-brand-primary/30 rounded text-[9px] font-semibold flex items-center gap-0.5 transition cursor-pointer"
                                        title="View original uploaded CV document"
                                      >
                                        <FileText className="w-2.5 h-2.5" /> Full CV
                                      </button>
                                    )}
                                    <ExternalLink className="w-3 h-3 text-purple-500 group-hover:translate-x-0.5 transition" />
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-1 text-[10px] opacity-60 text-right font-mono">
                        {m.timestamp}
                      </div>
                    </div>
                  </div>
                )
              })
            )}

            {loading && (
              <div className="flex flex-col gap-1.5 bg-purple-50 border border-purple-200 rounded-xl px-3 py-2.5 w-fit max-w-sm">
                <div className="flex items-center gap-2 text-xs text-purple-700 font-semibold">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-600" />
                  <span>Agentic RAG {activeStatus ? `▶ ${activeStatus}` : "initializing…"}</span>
                </div>
                {agentTrace.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {agentTrace.map((t, i) => (
                      <span key={i} className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${
                        t.status === 'done' ? 'bg-green-100 text-green-700' :
                        t.status === 'error' ? 'bg-red-100 text-red-700' :
                        'bg-purple-100 text-purple-700'
                      }`}>
                        ✓ {t.agent.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}


            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="p-3 border-t border-surface-border bg-white flex items-center gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about candidate evidence, requirements, or rubric scores…"
              disabled={loading}
              className="flex-1 px-3.5 py-2.5 border border-surface-border rounded-xl text-sm focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 outline-hidden"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl text-sm font-medium flex items-center gap-1.5 shadow-xs transition disabled:opacity-50 cursor-pointer"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>Ask</span>
            </button>
          </form>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* RICH CV CITATION INSPECTOR & DOCUMENT VIEWER MODAL                        */}
      {/* ========================================================================= */}
      {inspectorOpen && currentCitation && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-purple-200">
            {/* Modal Header */}
            <div className="p-4 border-b border-surface-border bg-gradient-to-r from-purple-50/80 via-white to-purple-50/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center shadow-2xs">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-heading font-bold text-base text-surface-text flex items-center gap-1.5">
                      {currentCitation.source}
                    </h3>
                    <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 font-mono text-[11px] font-semibold">
                      Page {currentCitation.page ?? 1}
                    </span>
                  </div>
                  <p className="text-[11px] text-surface-muted flex items-center gap-1.5">
                    <span>Talent Pool CV Inspector</span>
                    <span>•</span>
                    <span className="text-purple-700 font-medium">
                      Citation {activeCitationIndex + 1} of {activeCitations.length}
                    </span>
                  </p>
                </div>
              </div>

              {/* Header Actions */}
              <div className="flex items-center gap-2">
                {/* Previous / Next Citation */}
                {activeCitations.length > 1 && (
                  <div className="flex items-center bg-gray-100 rounded-lg p-0.5 border border-gray-200 mr-2">
                    <button
                      onClick={() => setActiveCitationIndex((prev) => Math.max(0, prev - 1))}
                      disabled={activeCitationIndex === 0}
                      className="p-1 rounded text-surface-text hover:bg-white disabled:opacity-40 transition cursor-pointer"
                      title="Previous citation"
                    >
                      <ArrowLeft className="w-3.5 h-3.5" />
                    </button>
                    <span className="px-2 text-xs font-mono text-surface-muted">
                      {activeCitationIndex + 1}/{activeCitations.length}
                    </span>
                    <button
                      onClick={() =>
                        setActiveCitationIndex((prev) => Math.min(activeCitations.length - 1, prev + 1))
                      }
                      disabled={activeCitationIndex === activeCitations.length - 1}
                      className="p-1 rounded text-surface-text hover:bg-white disabled:opacity-40 transition cursor-pointer"
                      title="Next citation"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                <button
                  onClick={() => handleCopyQuote(currentCitation.quote)}
                  className="px-2.5 py-1.5 rounded-lg border border-surface-border hover:bg-gray-50 text-surface-text text-xs flex items-center gap-1.5 transition cursor-pointer"
                  title="Copy cited quote to clipboard"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied!" : "Copy Quote"}</span>
                </button>

                {currentCitation.candidate_id && (
                  <button
                    onClick={() => {
                      setSelectedCvCandidate({
                        id: currentCitation.candidate_id!,
                        name: currentCitation.source.replace(/_CV\.(pdf|txt|docx)/i, "").replace(/_/g, " "),
                      })
                    }}
                    className="px-2.5 py-1.5 rounded-lg border border-brand-primary/30 bg-indigo-50 hover:bg-indigo-100 text-brand-primary text-xs font-semibold flex items-center gap-1.5 transition shadow-2xs cursor-pointer"
                    title="Open original uploaded CV document in full viewer"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>View Full Original CV</span>
                  </button>
                )}

                <button
                  onClick={() => setInspectorOpen(false)}
                  className="p-1.5 rounded-lg text-surface-muted hover:text-surface-text hover:bg-gray-100 transition cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Matched Excerpt Banner */}
            <div className="p-3 bg-amber-50/80 border-b border-amber-200/80 flex items-start gap-3">
              <div className="p-1.5 bg-amber-100 text-amber-800 rounded-lg shrink-0 mt-0.5">
                <Eye className="w-4 h-4" />
              </div>
              <div className="flex-1 text-xs">
                <div className="font-semibold text-amber-950 flex items-center gap-2">
                  <span>📌 Grounded Evidence Passage (Cited by Copilot):</span>
                  <span className="font-mono text-[10px] bg-amber-200/60 px-1.5 py-0.2 rounded text-amber-900">
                    Exact Match
                  </span>
                </div>
                <div className="mt-1 text-amber-900 font-medium italic bg-white/80 p-2.5 rounded-lg border border-amber-200 text-xs">
                  "{currentCitation.quote}"
                </div>
              </div>
            </div>

            {/* In-Document Search Bar */}
            <div className="px-4 py-2 bg-gray-50 border-b border-surface-border flex items-center gap-2 text-xs">
              <Search className="w-3.5 h-3.5 text-surface-muted" />
              <input
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter or search inside this candidate's CV text…"
                className="flex-1 bg-transparent border-none outline-hidden text-xs text-surface-text placeholder:text-surface-muted"
              />
              {searchFilter && (
                <button
                  onClick={() => setSearchFilter("")}
                  className="text-surface-muted hover:text-surface-text text-[10px] px-1 rounded"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Full Document Body View */}
            <div className="flex-1 overflow-y-auto p-4 bg-white text-xs font-mono leading-relaxed space-y-2">
              {(() => {
                const docText = currentCitation.full_context || currentCitation.quote || ""
                const quote = currentCitation.quote.trim()

                // Check if the quote is inside the full text
                const quoteIndex = quote ? docText.indexOf(quote) : -1

                if (quoteIndex !== -1) {
                  const before = docText.slice(0, quoteIndex)
                  const matched = docText.slice(quoteIndex, quoteIndex + quote.length)
                  const after = docText.slice(quoteIndex + quote.length)

                  return (
                    <div>
                      <div className="text-gray-600 whitespace-pre-wrap">{before}</div>
                      {/* Highlighted Cited Passage */}
                      <div
                        ref={highlightRef}
                        className="my-3 p-3.5 rounded-xl bg-amber-100 border-l-4 border-amber-500 shadow-sm text-amber-950 font-sans"
                      >
                        <div className="flex items-center justify-between text-[11px] font-bold text-amber-900 mb-1">
                          <span className="flex items-center gap-1.5">
                            ★ CITED RESUME SECTION (Page {currentCitation.page ?? 1})
                          </span>
                          <span className="font-mono text-[10px] bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded">
                            Verified Source
                          </span>
                        </div>
                        <p className="whitespace-pre-wrap font-medium text-xs leading-relaxed">
                          {matched}
                        </p>
                      </div>
                      <div className="text-gray-600 whitespace-pre-wrap">{after}</div>
                    </div>
                  )
                }

                // Fallback: render text with lines, and highlight search matches or quote
                return (
                  <div className="space-y-3">
                    <div
                      ref={highlightRef}
                      className="p-3.5 rounded-xl bg-amber-50 border-l-4 border-amber-500 text-amber-950 font-sans"
                    >
                      <div className="text-[11px] font-bold text-amber-900 mb-1">
                        ★ Cited Passage (Target Quote):
                      </div>
                      <p className="whitespace-pre-wrap text-xs italic">{quote}</p>
                    </div>

                    <div className="pt-2 border-t border-gray-100">
                      <div className="text-[10px] font-bold uppercase text-surface-muted mb-1 font-sans">
                        Full Document Content Context:
                      </div>
                      <div className="whitespace-pre-wrap text-gray-700 bg-gray-50/70 p-3 rounded-lg border border-gray-200">
                        {docText}
                      </div>
                    </div>
                  </div>
                )
              })()}
            </div>

            {/* Modal Footer */}
            <div className="p-3 bg-gray-50 border-t border-surface-border flex items-center justify-between text-xs text-surface-muted">
              <div className="flex items-center gap-2">
                <span className="font-medium text-surface-text">Document:</span>
                <span className="font-mono">{currentCitation.source}</span>
                <span>•</span>
                <span>Page: {currentCitation.page ?? 1}</span>
              </div>
              <button
                onClick={() => setInspectorOpen(false)}
                className="px-4 py-1.5 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-medium transition cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Full Original CV Document Viewer Modal */}
      <CvViewerModal
        candidateId={selectedCvCandidate?.id || null}
        candidateName={selectedCvCandidate?.name}
        isOpen={!!selectedCvCandidate}
        onClose={() => setSelectedCvCandidate(null)}
      />
    </div>
  )
}
