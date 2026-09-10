import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { Skeleton } from "../components/Skeleton"
import { Cpu, Zap, ArrowDownUp, CheckCircle2, AlertTriangle, Plus, Trash2, Sparkles } from "lucide-react"

interface AIConfig {
  gemini_api_key: string
  gemini_model: string
  fast_model: string
  model_priority_queue: string[]
  enable_priority_fallback: boolean
  task_routing_enabled: boolean
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
  const [customPrimaryModel, setCustomPrimaryModel] = useState("")
  const [customFastModel, setCustomFastModel] = useState("")
  const [newPriorityModel, setNewPriorityModel] = useState("")
  const [testResult, setTestResult] = useState<{
    ok: boolean
    text?: string
    error?: string
    model?: string
    requested_model?: string
    provider?: string
    cascaded?: boolean
    cascaded_from?: string
    cost_usd?: number
  } | null>(null)

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
      toast.success("AI configuration updated successfully")
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

  async function handleApplyCustomPrimary(e: React.FormEvent) {
    e.preventDefault()
    if (!customPrimaryModel.trim()) return
    await saveConfig({ gemini_model: customPrimaryModel.trim() })
    setCustomPrimaryModel("")
  }

  async function handleApplyCustomFast(e: React.FormEvent) {
    e.preventDefault()
    if (!customFastModel.trim()) return
    await saveConfig({ fast_model: customFastModel.trim() })
    setCustomFastModel("")
  }

  async function handleAddPriorityModel(e: React.FormEvent) {
    e.preventDefault()
    if (!newPriorityModel.trim() || !config) return
    const model = newPriorityModel.trim()
    const currentQueue = config.model_priority_queue || []
    if (currentQueue.includes(model)) {
      toast.error("Model already exists in priority queue")
      return
    }
    const updatedQueue = [...currentQueue, model]
    await saveConfig({ model_priority_queue: updatedQueue })
    setNewPriorityModel("")
  }

  async function handleRemovePriorityModel(index: number) {
    if (!config) return
    const updatedQueue = [...(config.model_priority_queue || [])]
    updatedQueue.splice(index, 1)
    await saveConfig({ model_priority_queue: updatedQueue })
  }

  async function testLLM() {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await apiClient.post("/admin/ai-test", { prompt: "Explain how AI works in a few words" })
      setTestResult(res.data)
      if (res.data.ok) {
        if (res.data.cascaded) {
          toast.success(`Cascade active: answered via ${res.data.model} (cascaded from ${res.data.cascaded_from})`)
        } else {
          toast.success(`LLM test passed via ${res.data.provider} (${res.data.model})`)
        }
        await load()
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
          <h2 className="text-2xl font-heading font-semibold text-surface-text">AI Architecture, Priority Queue & Telemetry</h2>
          <p className="text-sm text-surface-muted mt-1">
            Configure custom LLM models, automated priority limit cascades, and task-fit quota protection.
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
        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-xs">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Total LLM Calls</span>
            <span className="text-blue-600 font-bold">● Live</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            {usage?.calls ?? 0}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Multi-model priority executions
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-xs">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Estimated Cost (USD)</span>
            <span className="text-emerald-600 font-bold">API Pricing</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            ${(usage?.cost_usd ?? 0).toFixed(6)}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Live token cost ledger
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-xs">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Prompt Tokens</span>
            <span className="text-indigo-600 font-bold">Input</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            {(usage?.input_tokens ?? 0).toLocaleString()}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Prompt context & CV content
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-surface-border shadow-xs">
          <div className="flex items-center justify-between text-surface-muted text-xs font-semibold uppercase">
            <span>Completion Tokens</span>
            <span className="text-purple-600 font-bold">Output</span>
          </div>
          <div className="text-3xl font-bold text-surface-text mt-2">
            {(usage?.output_tokens ?? 0).toLocaleString()}
          </div>
          <div className="text-xs text-surface-muted mt-1">
            Generated rationales & rubrics
          </div>
        </div>
      </div>

      {/* Model Architecture & Custom Input */}
      <div className="bg-white p-6 rounded-xl border border-surface-border shadow-xs space-y-6">
        <div className="border-b border-surface-border pb-3 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-surface-text text-base flex items-center gap-2">
              <Cpu className="w-5 h-5 text-brand-primary" /> Model Architecture & Custom Selection
            </h3>
            <p className="text-xs text-surface-muted mt-0.5">
              Select from available Google models or type ANY custom model name directly.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Active: {config.gemini_model}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Primary Reasoning Model */}
          <div className="p-4 rounded-xl border border-surface-border bg-slate-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-indigo-600" /> Primary Reasoning Model
              </label>
              <span className="text-[11px] font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded font-medium">
                {config.gemini_model}
              </span>
            </div>
            <p className="text-xs text-surface-muted">
              Powers deep candidate screening, criteria scoring, Copilot chat, and Agentic RAG.
            </p>

            {/* Dropdown Selector */}
            <select
              value={config.available_models.includes(config.gemini_model) ? config.gemini_model : "custom"}
              onChange={(e) => {
                if (e.target.value !== "custom") {
                  saveConfig({ gemini_model: e.target.value })
                }
              }}
              disabled={saving}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white font-mono focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            >
              <optgroup label="Available Studio Models">
                {config.available_models.map((m) => (
                  <option key={m} value={m}>
                    {m} {m === config.gemini_model ? "✓ (Selected)" : ""}
                  </option>
                ))}
              </optgroup>
              <option value="custom">-- Type Custom Model Name Below --</option>
            </select>

            {/* Custom Model Input */}
            <form onSubmit={handleApplyCustomPrimary} className="flex gap-2 pt-1">
              <input
                type="text"
                placeholder="Or type any model (e.g. gemini-3.8-flash, nano-banana)"
                value={customPrimaryModel}
                onChange={(e) => setCustomPrimaryModel(e.target.value)}
                disabled={saving}
                className="flex-1 px-3 py-2 border border-surface-border rounded-lg text-xs font-mono bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              />
              <button
                type="submit"
                disabled={saving || !customPrimaryModel.trim()}
                className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg disabled:opacity-50 transition shadow-2xs whitespace-nowrap"
              >
                Set Custom
              </button>
            </form>
          </div>

          {/* Fast / High-Throughput Model */}
          <div className="p-4 rounded-xl border border-surface-border bg-slate-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-emerald-600" /> Fast / High-Throughput Model
              </label>
              <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-medium">
                {config.fast_model || "gemini-3.1-flash-lite"}
              </span>
            </div>
            <p className="text-xs text-surface-muted">
              Used for CV skill parsing & entity extraction to protect high-reasoning quotas (500 RPD, 15 RPM).
            </p>

            {/* Dropdown Selector */}
            <select
              value={config.available_models.includes(config.fast_model) ? config.fast_model : "custom"}
              onChange={(e) => {
                if (e.target.value !== "custom") {
                  saveConfig({ fast_model: e.target.value })
                }
              }}
              disabled={saving}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white font-mono focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            >
              <optgroup label="Recommended Fast Models">
                {config.available_models
                  .filter((m) => m.includes("lite") || m.includes("26b") || m.includes("flash"))
                  .map((m) => (
                    <option key={m} value={m}>
                      {m} {m === config.fast_model ? "✓ (Selected Fast)" : ""}
                    </option>
                  ))}
              </optgroup>
              <option value="custom">-- Type Custom Fast Model --</option>
            </select>

            {/* Custom Fast Model Input */}
            <form onSubmit={handleApplyCustomFast} className="flex gap-2 pt-1">
              <input
                type="text"
                placeholder="Or type custom fast model (e.g. gemini-3.1-flash-lite)"
                value={customFastModel}
                onChange={(e) => setCustomFastModel(e.target.value)}
                disabled={saving}
                className="flex-1 px-3 py-2 border border-surface-border rounded-lg text-xs font-mono bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              />
              <button
                type="submit"
                disabled={saving || !customFastModel.trim()}
                className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg disabled:opacity-50 transition shadow-2xs whitespace-nowrap"
              >
                Set Fast
              </button>
            </form>
          </div>
        </div>

        {/* API Authentication Key Form */}
        <div className="pt-2">
          <label className="block text-xs font-semibold text-surface-muted uppercase mb-1.5">Gemini API Key</label>
          <form onSubmit={handleKeySubmit} className="flex gap-2 max-w-xl">
            <input
              type="password"
              placeholder={config.gemini_api_key ? "••••••••••••••••••••••••" : "Paste AIzaSy... key"}
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              disabled={saving}
              className="flex-1 px-3.5 py-2 border border-surface-border rounded-lg text-sm focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            />
            <button
              type="submit"
              disabled={saving || !newKey.trim()}
              className="px-4 py-2 bg-brand-primary text-white text-xs font-semibold rounded-lg disabled:opacity-50 hover:bg-brand-primary/90 transition shadow-xs whitespace-nowrap"
            >
              Update Key
            </button>
          </form>
          <span className="text-[11px] text-surface-muted mt-1 block">
            API key is stored in container runtime and masked in responses.
          </span>
        </div>

        {/* Diagnostic Run Button */}
        <div className="pt-2 flex flex-wrap items-center gap-3">
          <button
            onClick={testLLM}
            disabled={testing || !config.ai_enabled}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition shadow-xs flex items-center gap-2"
          >
            {testing ? (
              <>
                <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                <span>Testing Priority Cascade...</span>
              </>
            ) : (
              <span>Run Live Diagnostic Test</span>
            )}
          </button>
          {testResult && (
            <div
              className={`text-xs px-4 py-2 rounded-lg font-medium border ${
                testResult.ok
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-red-50 text-red-800 border-red-200"
              }`}
            >
              {testResult.ok ? (
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>
                    Diagnostic Passed via <strong>{testResult.model}</strong>
                    {testResult.cascaded && (
                      <span className="ml-1 text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded text-[10px]">
                        (Cascaded from {testResult.cascaded_from})
                      </span>
                    )}
                    {" "}— Cost: ${ (testResult.cost_usd || 0).toFixed(6) }
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-600" />
                  <span>Error: {testResult.error}</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Model Priority Queue & Cascading Fallback Card */}
      <div className="bg-white p-6 rounded-xl border border-surface-border shadow-xs space-y-5">
        <div className="border-b border-surface-border pb-3 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div>
            <h3 className="font-semibold text-surface-text text-base flex items-center gap-2">
              <ArrowDownUp className="w-5 h-5 text-indigo-600" /> Priority Fallback Cascade Queue
            </h3>
            <p className="text-xs text-surface-muted mt-0.5">
              If a preferred model limit is exceeded (HTTP 429 / Quota), the engine automatically cascades to the next priority model.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs font-semibold text-surface-text cursor-pointer">
              <input
                type="checkbox"
                checked={config.enable_priority_fallback}
                onChange={(e) => saveConfig({ enable_priority_fallback: e.target.checked })}
                disabled={saving}
                className="w-4 h-4 text-brand-primary rounded"
              />
              <span>Auto-Cascade on Limit</span>
            </label>
            <label className="flex items-center gap-2 text-xs font-semibold text-surface-text cursor-pointer">
              <input
                type="checkbox"
                checked={config.task_routing_enabled}
                onChange={(e) => saveConfig({ task_routing_enabled: e.target.checked })}
                disabled={saving}
                className="w-4 h-4 text-emerald-600 rounded"
              />
              <span>Intelligent Task-Tier Routing</span>
            </label>
          </div>
        </div>

        {/* Visual Cascade Chain */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
            Active Cascade Sequence:
          </div>

          <div className="flex flex-col gap-2">
            {/* Primary Model is always step 1 */}
            <div className="flex items-center justify-between p-3 rounded-lg border border-indigo-300 bg-indigo-50/70">
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                  1
                </span>
                <span className="font-mono text-sm font-semibold text-indigo-950">{config.gemini_model}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-200 text-indigo-900 uppercase">
                  Primary Reasoning Model
                </span>
              </div>
              <span className="text-xs text-indigo-700 font-medium">Top Priority (Initial Choice)</span>
            </div>

            {/* Fallback Priority Queue Items */}
            {(config.model_priority_queue || [])
              .filter((m) => m !== config.gemini_model)
              .map((model, idx) => (
                <div
                  key={model}
                  className="flex items-center justify-between p-3 rounded-lg border border-surface-border bg-surface-page/30 hover:bg-surface-page transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-slate-200 text-slate-700 text-xs font-bold flex items-center justify-center">
                      {idx + 2}
                    </span>
                    <span className="font-mono text-sm font-medium text-slate-800">{model}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">
                      Fallback Tier {idx + 1}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleRemovePriorityModel(idx)}
                      disabled={saving}
                      className="p-1 text-slate-400 hover:text-red-600 transition"
                      title="Remove from cascade queue"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
          </div>

          {/* Add custom model to cascade */}
          <form onSubmit={handleAddPriorityModel} className="flex gap-2 pt-3">
            <input
              type="text"
              placeholder="Add another model to cascade queue (e.g. gemini-3.7-flash, gemma-4-31b-it)"
              value={newPriorityModel}
              onChange={(e) => setNewPriorityModel(e.target.value)}
              disabled={saving}
              className="flex-1 px-3 py-2 border border-surface-border rounded-lg text-xs font-mono bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            />
            <button
              type="submit"
              disabled={saving || !newPriorityModel.trim()}
              className="px-3.5 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg disabled:opacity-50 transition shadow-2xs flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" /> Add to Queue
            </button>
          </form>
        </div>
      </div>

      {/* Feature Toggles */}
      <div className="bg-white p-6 rounded-xl border border-surface-border shadow-xs space-y-4">
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
      <div className="bg-white rounded-xl border border-surface-border shadow-xs overflow-hidden">
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
                    No individual model records accumulated yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Records Stream */}
      {recentRecords.length > 0 && (
        <div className="bg-white rounded-xl border border-surface-border shadow-xs overflow-hidden">
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
      <div className="bg-white p-6 rounded-xl border border-surface-border shadow-xs space-y-3">
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
