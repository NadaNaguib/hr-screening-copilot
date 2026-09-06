import { useState } from "react"
import { Loader2 } from "lucide-react"
import { createSSEConnection, SSEStatus } from "../lib/sse"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1"

export function CopilotChat() {
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [citations, setCitations] = useState<{ quote: string; source: string; page: number | null }[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<SSEStatus>("closed")

  function ask(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim()) return

    setAnswer("")
    setCitations([])
    setLoading(true)
    setStatus("connecting")

    const cleanup = createSSEConnection({
      url: `${API_BASE}/chat`,
      body: { question },
      onStatus: setStatus,
      onEvent: (event) => {
        if (event.type === "answer_chunk") {
          setAnswer((prev) => prev + (typeof event.data === "string" ? event.data : ""))
          const cites = (event.data as any)?.citations || (event as any).citations
          if (Array.isArray(cites) && cites.length > 0) {
            setCitations(cites)
          }
        } else if (event.type === "done" || (event as any).event === "done") {
          setLoading(false)
          setStatus("closed")
        }
      },
    })

    return () => {
      cleanup()
      setLoading(false)
    }
  }

  const statusText = {
    connecting: "Connecting…",
    open: "Streaming…",
    error: "Connection lost — retrying…",
    closed: "",
  }[status]

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-heading font-semibold text-surface-text">Copilot Chat</h2>
      <form onSubmit={ask} className="bg-white p-4 rounded-lg border border-surface-border flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about a candidate or job..."
          className="flex-1 px-3 py-2 border border-surface-border rounded-md"
        />
        <button type="submit" className="px-4 py-2 bg-brand-primary text-white rounded-md flex items-center gap-2" disabled={loading}>
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {loading ? "Asking..." : "Ask"}
        </button>
      </form>

      {statusText && (
        <div className={`text-sm px-3 py-2 rounded-md inline-flex items-center gap-2 ${
          status === "error" ? "bg-semantic-danger/10 text-semantic-danger" : "bg-semantic-info/10 text-semantic-info"
        }`}>
          {status === "error" && <span className="w-2 h-2 rounded-full bg-semantic-danger animate-pulse" />}
          {statusText}
        </div>
      )}

      {answer && (
        <div className="bg-white p-4 rounded-lg border border-surface-border">
          <h3 className="font-medium mb-2">Answer</h3>
          <p className="whitespace-pre-wrap">{answer}</p>
          {citations.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-surface-muted mb-1">Citations</h4>
              <ul className="text-sm space-y-1">
                {citations.map((c, i) => (
                  <li key={i} className="text-surface-muted">[{i + 1}] {c.quote} — {c.source}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
