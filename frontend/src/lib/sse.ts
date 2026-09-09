export type SSEEvent = {
  type: string
  data: unknown
}

export type SSEStatus = "connecting" | "open" | "closed" | "error"

export interface SSEOptions {
  url: string
  body?: Record<string, unknown>
  onEvent: (event: SSEEvent) => void
  onStatus?: (status: SSEStatus) => void
  maxRetries?: number
}

export function createSSEConnection(options: SSEOptions): () => void {
  const { url, body, onEvent, onStatus, maxRetries = 5 } = options
  let retryCount = 0
  let delay = 1000
  let abortController: AbortController | null = null
  let active = true

  const setStatus = (status: SSEStatus) => {
    onStatus?.(status)
  }

  const connect = async () => {
    if (!active) return
    setStatus("connecting")
    abortController = new AbortController()

    try {
      const response = await fetch(url, {
        method: body ? "POST" : "GET",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          Authorization: `Bearer ${localStorage.getItem("token") || ""}`,
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      if (!response.body) {
        throw new Error("No response body")
      }

      setStatus("open")
      retryCount = 0
      delay = 1000

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (active) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith("data:")) continue
          const payload = trimmed.replace(/^data:\s*/, "").trim()
          if (payload === "[DONE]") {
            active = false
            reader.cancel()
            setStatus("closed")
            return
          }
          try {
            const parsed = JSON.parse(payload)
            onEvent(parsed)
          } catch {
            onEvent({ type: "raw", data: payload })
          }
        }
      }

      setStatus("closed")
    } catch (err) {
      if (!active) return
      setStatus("error")
      if (retryCount < maxRetries) {
        retryCount++
        const timeout = setTimeout(() => {
          delay = Math.min(delay * 2, 30000)
          connect()
        }, delay)
        return () => clearTimeout(timeout)
      }
      setStatus("closed")
    }
  }

  connect()

  return () => {
    active = false
    abortController?.abort()
  }
}
