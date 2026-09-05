import { useEffect, useState } from "react"
import { apiClient } from "../lib/apiClient"

export function Observability() {
  const [settings, setSettings] = useState({ simulate_agent_failure: false, gemini_model: "", log_level: "" })
  const [cost, setCost] = useState({ calls: 0, input_tokens: 0, output_tokens: 0, cost_usd: 0 })

  useEffect(() => {
    apiClient.get("/observability/settings").then((r) => setSettings(r.data))
    apiClient.get("/observability/token-cost").then((r) => setCost(r.data))
  }, [])

  async function toggleSimulate() {
    const newValue = !settings.simulate_agent_failure
    await apiClient.post(`/observability/simulate-agent-failure?value=${newValue}`)
    setSettings((s) => ({ ...s, simulate_agent_failure: newValue }))
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-semibold text-surface-text">Observability</h2>
      <div className="bg-white p-4 rounded-lg border border-surface-border grid grid-cols-2 gap-4">
        <div><div className="text-sm text-surface-muted">LLM Calls</div><div className="text-xl font-semibold">{cost.calls}</div></div>
        <div><div className="text-sm text-surface-muted">Cost USD</div><div className="text-xl font-semibold">${cost.cost_usd.toFixed(4)}</div></div>
        <div><div className="text-sm text-surface-muted">Input Tokens</div><div className="text-xl font-semibold">{cost.input_tokens}</div></div>
        <div><div className="text-sm text-surface-muted">Output Tokens</div><div className="text-xl font-semibold">{cost.output_tokens}</div></div>
      </div>
      <div className="bg-white p-4 rounded-lg border border-surface-border">
        <h3 className="font-medium mb-2">Settings</h3>
        <div className="flex items-center justify-between">
          <span>SIMULATE_AGENT_FAILURE</span>
          <button
            onClick={toggleSimulate}
            className={`px-4 py-2 rounded-md text-white ${settings.simulate_agent_failure ? "bg-semantic-danger" : "bg-semantic-success"}`}
          >
            {settings.simulate_agent_failure ? "ON" : "OFF"}
          </button>
        </div>
        <div className="mt-2 text-sm text-surface-muted">Model: {settings.gemini_model}</div>
      </div>
    </div>
  )
}
