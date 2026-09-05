import { useState } from "react"
import { apiClient } from "../lib/apiClient"

export function CopilotChat() {
  const [question, setQuestion] = useState("")
  const [answer, setAnswer] = useState("")
  const [citations, setCitations] = useState<{ quote: string; source: string; page: number | null }[]>([])
  const [loading, setLoading] = useState(false)

  async function ask(e: React.FormEvent) {
    e.preventDefault()
    setAnswer("")
    setCitations([])
    setLoading(true)
    try {
      const res = await apiClient.post("/chat", { question }, { responseType: "text" })
      // Simple non-SSE fallback: parse lines
      const lines = res.data.split("\n").filter((l: string) => l.startsWith("data:"))
      let full = ""
      let cites: any[] = []
      for (const line of lines) {
        try {
          const parsed = JSON.parse(line.replace("data:", "").trim())
          if (parsed.type === "answer_chunk") {
            full += parsed.data
            if (parsed.citations) cites = parsed.citations
          }
        } catch {}
      }
      setAnswer(full || "(no answer)")
      setCitations(cites)
    } finally {
      setLoading(false)
    }
  }

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
        <button type="submit" className="px-4 py-2 bg-brand-primary text-white rounded-md" disabled={loading}>
          {loading ? "Asking..." : "Ask"}
        </button>
      </form>
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
