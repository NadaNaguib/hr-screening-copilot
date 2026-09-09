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

interface RecentRecord {
  provider: string
  model: string
  input_tokens: number
  output_tokens: number
  cost_usd: number
  correlation_id: string
}

export function AISettings() {
  const [config, setConfig] = useState<AIConfig | null>(null)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [recentRecords, setRecentRecords] = useState<RecentRecord[]>([])
  const [failures, setFailures] = useState<Failure[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [newKey, setNewKey] = useState("")
  const [testResult, setTestResult] = useState<{ok: boolean; text?: string; error?: string; model?: string; provider?: string; cost_usd?: number} | null>(null)

  async function load() {
    try {
      const [cfgRes, usageRes] = await Promise.all([
        apiClient.get("/admin/ai-config"),
        apiClient.get("/admin/ai-usage"),
      ])
      setConfig(cfgRes.data)
      setUsage(usageRes.data.usage)
      setRecentRecords(usageRes.data.recent_records || [])
      setFailures(usageRes.data.failures || [])
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || "Failed to load AI settings")
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
      toast.success("AI configuration saved")
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || "Failed to update AI settings")
    } finally {
      setSaving(false)
    }
  }

  async function handleKeySubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!newKey.trim()) return
    await saveConfig({ gemini_api_key: newKey.trim() })
    setNewKey("")
  }

  async function testLLM() {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await apiClient.post("/admin/ai-test", { prompt: "Explain how AI works in a few words" })
      setTestResult(res.data)
      if (res.data.ok) {
        toast.success(`LLM test passed via ${res.data.provider} (${res.data.model})`)
        await load() // refresh real metrics
      } else {
        toast.error(res.data.error || "LLM test failed")
      }
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || "Test request failed")
    } finally {
      setTesting(false)
    }
  }

  if (loading || !config) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">AI Control Panel & Telemetry</h2>
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-heading font-semibold text-surface-text">AI Control Panel & Model Telemetry</h2>
          <p className="text-sm text-surface-muted mt-1">
            Real-time LLM configuration, multi-adapter fallback monitoring, and live token usage ledger.
          </p>
        </div>
        <button
          onClick={load}
          className="self-start md:self-auto px-4 py-2 text-xs font-semibold bg-surface-page hover:bg-surface-border text-surface-text rounded-lg border border-surface-border transition flex items-center gap-1.5"
        >
          <span>↻</span> Refresh Live Metrics
        </button>
      </div>

      {/* Real-time Dynamic Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-sm">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Total LLM Calls</span>
            <span className="text-blue-600 font-bold">● Live</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            {usage?.calls ?? 0}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Across REST & SDK adapters
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-sm">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Estimated Cost (USD)</span>
            <span className="text-emerald-600 font-bold">API Pricing</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            ${(usage?.cost_usd ?? 0).toFixed(6)}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Gemini 2.5 Flash rate calculation
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-sm">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Prompt Tokens</span>
            <span className="text-indigo-600 font-bold">Input</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            {(usage?.input_tokens ?? 0).toLocaleString()}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Tokens sent into LLM context
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-sm">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Completion Tokens</span>
            <span className="text-purple-600 font-bold">Output</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            {(usage?.output_tokens ?? 0).toLocaleString()}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Generated responses & rationales
          </div>
        </div>
      </div>

      {/* Model & Key Configuration */}
      <div className="bg-white p-6 rounded-xl border border-surface-border shadow-sm space-y-5">
        <div className="border-b border-surface-border pb-3">
          <h3 className="font-semibold text-surface-text text-base">Model Architecture & Credentials</h3>
          <p className="text-xs text-surface-muted mt-0.5">Switch active LLM backbone or update API authentication keys.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1.5">Selected Foundation Model</label>
            <select
              value={config.gemini_model}
              onChange={(e) => saveConfig({ gemini_model: e.target.value })}
              disabled={saving}
              className="w-full px-3.5 py-2.5 border border-surface-border rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            >
              {config.available_models.map((m) => {
                let label = m
                if (m === "gemini-2.5-flash") label = `${m} (Recommended Flash)`
                else if (m === "gemini-3.1-pro-preview") label = `${m} (Pro Model)`
                else if (m === "gemini-2.5-flash-lite") label = `${m} (Fast Lite)`
                return (
                  <option key={m} value={m}>{label}</option>
                )
              })}
            </select>
            <span className="text-[11px] text-surface-muted mt-1 block">
              Multi-adapter fallback switches from Gemini REST to SDK if primary adapter fails.
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1.5">Gemini API Key</label>
            <form onSubmit={handleKeySubmit} className="flex gap-2">
              <input
                type="password"
                placeholder={config.gemini_api_key ? "••••••••••••••••••••••••" : "Paste AIzaSy... key"}
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                disabled={saving}
                className="flex-1 px-3.5 py-2.5 border border-surface-border rounded-lg text-sm focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              />
              <button
                type="submit"
                disabled={saving || !newKey.trim()}
                className="px-4 py-2.5 bg-brand-primary text-white text-xs font-semibold rounded-lg disabled:opacity-50 hover:bg-brand-primary/90 transition shadow-sm"
              >
                Update Key
              </button>
            </form>
            <span className="text-[11px] text-surface-muted mt-1 block">
              Key is securely stored in container environment and masked in responses.
            </span>
          </div>
        </div>

        <div className="pt-2 flex flex-wrap items-center gap-3">
          <button
            onClick={testLLM}
            disabled={testing || !config.ai_enabled}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition shadow-sm flex items-center gap-2"
          >
            {testing ? <span>Testing Endpoint...</span> : <span>Run Live LLM Diagnostic Test</span>}
          </button>
          {testResult && (
            <div className={`text-xs px-3.5 py-2 rounded-lg font-medium ${testResult.ok ? "bg-emerald-50 text-emerald-800 border border-emerald-200" : "bg-red-50 text-red-800 border border-red-200"}`}>
              {testResult.ok
                ? `✔ Diagnostic Passed via ${testResult.provider} (${testResult.model}) — Cost: $${(testResult.cost_usd || 0).toFixed(6)}`
                : `✖ Error: ${testResult.error}`}
            </div>
          )}
        </div>
      </div>

      {/* Feature Toggles */}
      <div className="bg-white p-6 rounded-xl border border-surface-border shadow-sm space-y-4">
        <div className="border-b border-surface-border pb-3">
          <h3 className="font-semibold text-surface-text text-base">Pipeline Feature Flags</h3>
          <p className="text-xs text-surface-muted mt-0.5">Toggle system modes to test degradation pathways and offline behaviour.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { key: "ai_enabled", label: "Master AI Engine", desc: "Enable or globally freeze all external LLM provider calls" },
            { key: "plain_rag_enabled", label: "Plain RAG (Dense + BM25)", desc: "Direct hybrid search context retrieval without LangGraph orchestration" },
            { key: "agentic_rag_enabled", label: "Agentic RAG Orchestrator", desc: "Multi-agent LangGraph pipeline (Extractor, BiasGuard, Scorer, Drafter)" },
          ].map(({ key, label, desc }) => {
            const value = config[key as keyof AIConfig] as boolean
            return (
              <div key={key} className="p-4 border border-surface-border rounded-xl flex flex-col justify-between hover:border-brand-primary/40 transition">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-surface-text">{label}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${value ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-700"}`}>
                      {value ? "ACTIVE" : "OFFLINE"}
                    </span>
                  </div>
                  <p className="text-xs text-surface-muted leading-relaxed">{desc}</p>
                </div>
                <div className="mt-4 pt-3 border-t border-surface-border flex justify-end">
                  <button
                    onClick={() => saveConfig({ [key]: !value } as Partial<AIConfig>)}
                    disabled={saving}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white transition disabled:opacity-50 ${value ? "bg-emerald-600 hover:bg-emerald-700" : "bg-gray-600 hover:bg-gray-700"}`}
                  >
                    Switch {value ? "OFF" : "ON"}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Per-model usage table */}
      <div className="bg-white rounded-xl border border-surface-border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="font-semibold text-surface-text text-base">Breakdown by Provider & Model</h3>
          <span className="text-xs text-surface-muted">Dynamic Telemetry</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface-page text-surface-muted uppercase text-xs">
              <tr>
                <th className="px-6 py-3">Provider</th>
                <th className="px-6 py-3">Model</th>
                <th className="px-6 py-3">Invocations</th>
                <th className="px-6 py-3">Input Tokens</th>
                <th className="px-6 py-3">Output Tokens</th>
                <th className="px-6 py-3">Accumulated Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {usage && Object.keys(usage.models).length > 0 ? (
                Object.values(usage.models).map((m) => (
                  <tr key={`${m.provider}:${m.model}`} className="hover:bg-surface-page/50 transition">
                    <td className="px-6 py-3.5 font-medium text-surface-text">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700 font-mono">
                        {m.provider}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-surface-text font-mono text-xs">{m.model}</td>
                    <td className="px-6 py-3.5 font-semibold text-surface-text">{m.calls}</td>
                    <td className="px-6 py-3.5 text-surface-muted">{m.input_tokens.toLocaleString()}</td>
                    <td className="px-6 py-3.5 text-surface-muted">{m.output_tokens.toLocaleString()}</td>
                    <td className="px-6 py-3.5 font-semibold text-emerald-700 font-mono text-xs">
                      ${m.cost_usd.toFixed(6)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-surface-muted text-xs">
                    No individual model records accumulated yet. Run a screening pipeline or chat query to generate live records.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Records Stream */}
      {recentRecords.length > 0 && (
        <div className="bg-white rounded-xl border border-surface-border shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
            <h3 className="font-semibold text-surface-text text-base">Recent LLM Invocations Log</h3>
            <span className="text-xs text-surface-muted">Last {recentRecords.length} calls</span>
          </div>
          <div className="overflow-x-auto max-h-72">
            <table className="w-full text-xs text-left">
              <thead className="bg-surface-page text-surface-muted uppercase text-[10px] sticky top-0">
                <tr>
                  <th className="px-6 py-2.5">Correlation ID</th>
                  <th className="px-6 py-2.5">Provider</th>
                  <th className="px-6 py-2.5">Model</th>
                  <th className="px-6 py-2.5">Input</th>
                  <th className="px-6 py-2.5">Output</th>
                  <th className="px-6 py-2.5">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border font-mono">
                {recentRecords.slice(-20).reverse().map((r, i) => (
                  <tr key={i} className="hover:bg-surface-page/50">
                    <td className="px-6 py-2 text-surface-muted truncate max-w-[140px]">{r.correlation_id || "—"}</td>
                    <td className="px-6 py-2 text-surface-text">{r.provider}</td>
                    <td className="px-6 py-2 text-surface-text">{r.model}</td>
                    <td className="px-6 py-2 text-surface-muted">{r.input_tokens}</td>
                    <td className="px-6 py-2 text-surface-muted">{r.output_tokens}</td>
                    <td className="px-6 py-2 text-emerald-700">${r.cost_usd.toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent Failures */}
      <div className="bg-white p-6 rounded-xl border border-surface-border shadow-sm space-y-3">
        <div className="border-b border-surface-border pb-3 flex items-center justify-between">
          <h3 className="font-semibold text-surface-text text-base">Fallback & Failure Log</h3>
          <span className="text-xs text-surface-muted">Recorded Degrades</span>
        </div>
        {failures.length === 0 ? (
          <div className="text-xs text-surface-muted py-3">No system failures or provider timeouts recorded.</div>
        ) : (
          <div className="space-y-2.5 max-h-64 overflow-auto">
            {failures.slice(-15).reverse().map((f, i) => (
              <div key={i} className="p-3.5 bg-red-50/70 border border-red-200/80 rounded-lg text-xs">
                <div className="flex items-center justify-between text-red-900 font-semibold">
                  <span>{f.provider} / {f.model}</span>
                  <span className="text-[11px] text-red-600 font-normal">{f.timestamp ? new Date(f.timestamp).toLocaleTimeString() : ""}</span>
                </div>
                <div className="text-red-700 mt-1 font-mono text-[11px] break-all">{f.error}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
