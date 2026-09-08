import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { Skeleton } from "../components/Skeleton"

interface AIConfig {
  gemini_api_key: string
  gemini_model: string
  ai_enabled: boolean
  plain_rag_enabled: boolean
  agentic_rag_enabled: boolean
  available_models: string[]
}

interface UsageModel {
  provider: string
  model: string
  calls: number
  input_tokens: number
  output_tokens: number
  cost_usd: number
}

interface Usage {
  calls: number
  input_tokens: number
  output_tokens: number
  cost_usd: number
  models: Record<string, UsageModel>
}

interface Failure {
  provider: string
  model: string
  error: string
  correlation_id: string
  timestamp: string
}

export function AISettings() {
  const [config, setConfig] = useState<AIConfig | null>(null)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [failures, setFailures] = useState<Failure[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ok: boolean; text?: string; error?: string; model?: string; provider?: string} | null>(null)

  async function load() {
    try {
      const [cfgRes, usageRes] = await Promise.all([
        apiClient.get("/admin/ai-config"),
        apiClient.get("/admin/ai-usage"),
      ])
      setConfig(cfgRes.data)
      setUsage(usageRes.data.usage)
      setFailures(usageRes.data.failures || [])
    } catch (err: any) {
      toast.error(err.message || "Failed to load AI settings")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function saveConfig(updates: Partial<AIConfig>) {
    if (!config) return
    setSaving(true)
    try {
      const res = await apiClient.post("/admin/ai-config", updates)
      setConfig({ ...config, ...res.data })
      toast.success("AI settings updated")
    } catch (err: any) {
      toast.error(err.message || "Failed to update AI settings")
    } finally {
      setSaving(false)
    }
  }

  async function testLLM() {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await apiClient.post("/admin/ai-test", { prompt: "Explain how AI works in a few words" })
      setTestResult(res.data)
      if (res.data.ok) toast.success(`Test succeeded via ${res.data.provider}`)
      else toast.error(res.data.error || "Test failed")
    } catch (err: any) {
      toast.error(err.message || "Test request failed")
    } finally {
      setTesting(false)
    }
  }

  if (loading || !config) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">AI Control Panel</h2>
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-semibold text-surface-text">AI Control Panel</h2>

      <div className="bg-white p-4 rounded-lg border border-surface-border space-y-4">
        <h3 className="font-medium">Model & Key</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-surface-muted mb-1">Gemini Model</label>
            <select
              value={config.gemini_model}
              onChange={(e) => saveConfig({ gemini_model: e.target.value })}
              disabled={saving}
              className="w-full px-3 py-2 border rounded-md disabled:opacity-50"
            >
              {config.available_models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-surface-muted mb-1">API Key</label>
            <input
              type="password"
              placeholder={config.gemini_api_key ? "••••••••••••" : "Enter Gemini API key"}
              onChange={(e) => {
                if (e.target.value) saveConfig({ gemini_api_key: e.target.value })
              }}
              disabled={saving}
              className="w-full px-3 py-2 border rounded-md disabled:opacity-50"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={testLLM}
            disabled={testing || !config.ai_enabled}
            className="px-4 py-2 bg-brand-primary text-white rounded-md disabled:opacity-50"
          >
            {testing ? "Testing..." : "Test LLM"}
          </button>
          {testResult && (
            <div className={`text-sm px-3 py-2 rounded-md ${testResult.ok ? "bg-semantic-success/10 text-semantic-success" : "bg-semantic-danger/10 text-semantic-danger"}`}>
              {testResult.ok ? `OK (${testResult.provider} / ${testResult.model})` : `Failed: ${testResult.error}`}
            </div>
          )}
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg border border-surface-border space-y-4">
        <h3 className="font-medium">Feature Toggles</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { key: "ai_enabled", label: "AI Enabled" },
            { key: "plain_rag_enabled", label: "Plain RAG" },
            { key: "agentic_rag_enabled", label: "Agentic RAG" },
          ].map(({ key, label }) => {
            const value = config[key as keyof AIConfig] as boolean
            return (
              <div key={key} className="flex items-center justify-between p-3 border rounded-md">
                <span className="text-sm font-medium">{label}</span>
                <button
                  onClick={() => saveConfig({ [key]: !value } as Partial<AIConfig>)}
                  disabled={saving}
                  className={`px-3 py-1 rounded-md text-white text-sm disabled:opacity-50 ${value ? "bg-semantic-success" : "bg-semantic-danger"}`}
                >
                  {value ? "ON" : "OFF"}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg border border-surface-border space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Usage</h3>
          <button onClick={load} className="text-sm text-brand-primary hover:underline">Refresh</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><div className="text-sm text-surface-muted">LLM Calls</div><div className="text-xl font-semibold">{usage?.calls ?? 0}</div></div>
          <div><div className="text-sm text-surface-muted">Cost USD</div><div className="text-xl font-semibold">${(usage?.cost_usd ?? 0).toFixed(4)}</div></div>
          <div><div className="text-sm text-surface-muted">Input Tokens</div><div className="text-xl font-semibold">{usage?.input_tokens ?? 0}</div></div>
          <div><div className="text-sm text-surface-muted">Output Tokens</div><div className="text-xl font-semibold">{usage?.output_tokens ?? 0}</div></div>
        </div>
        {usage && Object.keys(usage.models).length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2">Per-model usage</h4>
            <table className="w-full text-sm text-left">
              <thead className="bg-surface-page text-surface-muted uppercase"><tr><th className="px-4 py-2">Provider</th><th className="px-4 py-2">Model</th><th className="px-4 py-2">Calls</th><th className="px-4 py-2">Tokens</th><th className="px-4 py-2">Cost</th></tr></thead>
              <tbody>
                {Object.values(usage.models).map((m) => (
                  <tr key={`${m.provider}:${m.model}`} className="border-t border-surface-border">
                    <td className="px-4 py-2">{m.provider}</td>
                    <td className="px-4 py-2">{m.model}</td>
                    <td className="px-4 py-2">{m.calls}</td>
                    <td className="px-4 py-2">{m.input_tokens + m.output_tokens}</td>
                    <td className="px-4 py-2">${m.cost_usd.toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white p-4 rounded-lg border border-surface-border space-y-4">
        <h3 className="font-medium">Recent Failures</h3>
        {failures.length === 0 ? (
          <div className="text-sm text-surface-muted">No failures recorded.</div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-auto">
            {failures.map((f, i) => (
              <div key={i} className="p-3 bg-semantic-danger/5 border border-semantic-danger/20 rounded-md text-sm">
                <div className="font-medium">{f.provider} / {f.model}</div>
                <div className="text-surface-muted text-xs">{f.timestamp}</div>
                <div className="text-semantic-danger mt-1">{f.error}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
