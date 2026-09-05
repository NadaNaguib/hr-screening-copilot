import { useEffect, useState } from "react"
import { apiClient } from "../lib/apiClient"
import { isAdmin } from "../lib/auth"

interface SLARule {
  id: string
  job_id: string | null
  priority: string
  triage_hours: number
  decision_hours: number
  active: boolean
}

export function SettingsSlaRules() {
  const [rules, setRules] = useState<SLARule[]>([])
  const [form, setForm] = useState({ priority: "medium", triage_hours: 48, decision_hours: 48 })

  useEffect(() => {
    fetchRules()
  }, [])

  async function fetchRules() {
    const res = await apiClient.get("/admin/sla-rules")
    setRules(res.data)
  }

  async function saveRule(e: React.FormEvent) {
    e.preventDefault()
    await apiClient.post("/admin/sla-rules", form)
    fetchRules()
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-semibold text-surface-text">SLA Rules</h2>
      {isAdmin() && (
        <form onSubmit={saveRule} className="bg-white p-4 rounded-lg border border-surface-border grid grid-cols-3 gap-4">
          <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} className="px-3 py-2 border rounded-md">
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <input type="number" value={form.triage_hours} onChange={(e) => setForm({ ...form, triage_hours: Number(e.target.value) })} placeholder="Triage hours" className="px-3 py-2 border rounded-md" />
          <input type="number" value={form.decision_hours} onChange={(e) => setForm({ ...form, decision_hours: Number(e.target.value) })} placeholder="Decision hours" className="px-3 py-2 border rounded-md" />
          <button type="submit" className="col-span-3 px-4 py-2 bg-brand-primary text-white rounded-md">Save Rule</button>
        </form>
      )}
      <div className="bg-white rounded-lg border border-surface-border overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase"><tr><th className="px-4 py-3">Priority</th><th className="px-4 py-3">Triage</th><th className="px-4 py-3">Decision</th><th className="px-4 py-3">Active</th></tr></thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id} className="border-t border-surface-border"><td className="px-4 py-3">{r.priority}</td><td className="px-4 py-3">{r.triage_hours}h</td><td className="px-4 py-3">{r.decision_hours}h</td><td className="px-4 py-3">{r.active ? "Yes" : "No"}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
