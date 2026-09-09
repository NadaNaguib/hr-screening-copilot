import { useState, useEffect, useRef } from "react"
import {
  Send,
  Loader2,
  Plus,
  Trash2,
  MessageSquare,
  Sparkles,
  BookOpen,
  FileText,
  ExternalLink,
  ChevronRight,
  User,
  Bot,
} from "lucide-react"
import { createSSEConnection, SSEStatus } from "../lib/sse"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1"

export interface Citation {
  quote: string
  source: string
  page: number | null
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  citations?: Citation[]
  timestamp: string
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
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
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
    setSelectedCitation(null)
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

    const cleanup = createSSEConnection({
      url: `${API_BASE}/chat`,
      body: { question: questionText },
      onStatus: setStatus,
      onEvent: (event: any) => {
        if (event.type === "answer_chunk") {
          const chunk = typeof event.data === "string" ? event.data : ""
          accumulatedAnswer += chunk

          const cites = event.citations || event.data?.citations
          if (Array.isArray(cites) && cites.length > 0) {
            accumulatedCitations = cites
          }

          setSessions((prev) =>
            prev.map((s) =>
              s.id === currentSessionId
                ? {
                    ...s,
                    messages: s.messages.map((m) =>
                      m.id === assistantPlaceholderId
                        ? {
                            ...m,
                            content: accumulatedAnswer,
                            citations: accumulatedCitations,
                          }
                        : m
                    ),
                  }
                : s
            )
          )
        } else if (event.type === "done" || event.event === "done") {
          setLoading(false)
          setStatus("closed")
        }
      },
    })

    cancelStreamRef.current = () => {
      cleanup()
      setLoading(false)
      setStatus("closed")
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] min-h-[550px] space-y-3">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-heading font-bold text-surface-text tracking-tight flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-purple-600" /> HR Screening Copilot
          </h2>
          <p className="text-xs text-surface-muted">
            Domain RAG assistant with grounded citations, semantic search, and audit trail verification.
          </p>
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

        {/* Center & Right: Chat Area + Citation Inspector */}
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
                    Ask questions about applicant competencies, compare qualifications against job rubrics, or verify screening evidence with citations.
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
                      <div className="whitespace-pre-wrap leading-relaxed">
                        {m.content ? (
                          m.content
                        ) : (
                          <div className="flex items-center gap-2 text-surface-muted text-xs italic">
                            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Retrieving context & synthesizing response…
                          </div>
                        )}
                      </div>

                      {/* Interactive Grounded Citations */}
                      {m.citations && m.citations.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-surface-border/60">
                          <div className="text-xs font-semibold text-purple-900 flex items-center gap-1 mb-2">
                            <BookOpen className="w-3.5 h-3.5 text-purple-600" />
                            Grounded References ({m.citations.length})
                          </div>
                          <div className="grid grid-cols-1 gap-2">
                            {m.citations.map((cite, idx) => (
                              <div
                                key={idx}
                                onClick={() => setSelectedCitation(cite)}
                                className="p-2.5 rounded-lg border border-purple-100 bg-white hover:bg-purple-50/70 hover:border-purple-300 transition cursor-pointer text-xs"
                              >
                                <div className="flex items-center justify-between text-purple-900 font-semibold mb-1">
                                  <span className="flex items-center gap-1">
                                    <FileText className="w-3 h-3 text-purple-600" /> [{idx + 1}] {cite.source}
                                  </span>
                                  {cite.page !== null && (
                                    <span className="text-[10px] px-1.5 py-0.2 bg-purple-100 text-purple-800 rounded font-mono">
                                      Page {cite.page}
                                    </span>
                                  )}
                                </div>
                                <p className="text-surface-muted italic line-clamp-2">
                                  "{cite.quote}"
                                </p>
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
              <div className="flex items-center gap-2 text-xs text-purple-700 bg-purple-50 px-3 py-2 rounded-lg border border-purple-200 w-fit">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-600" />
                <span>Agentic RAG is streaming evidence from database…</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Citation Inspector Modal / Bottom Sheet */}
          {selectedCitation && (
            <div className="p-3 bg-purple-50 border-t border-purple-200 flex items-start justify-between gap-3 text-xs">
              <div className="space-y-1">
                <div className="font-semibold text-purple-950 flex items-center gap-1.5">
                  <ExternalLink className="w-3.5 h-3.5 text-purple-600" /> Citation Source: {selectedCitation.source} (Page {selectedCitation.page ?? 0})
                </div>
                <div className="text-purple-900 bg-white p-2 rounded border border-purple-200 font-mono text-[11px]">
                  "{selectedCitation.quote}"
                </div>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-purple-700 hover:text-purple-950 font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>
          )}

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
              className="px-4 py-2.5 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl text-sm font-medium flex items-center gap-1.5 shadow-xs transition disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>Ask</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
