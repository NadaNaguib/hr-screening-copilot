import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { Skeleton } from "../components/Skeleton"

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
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchRules()
  }, [])

  async function fetchRules() {
    try {
      const res = await apiClient.get("/admin/sla-rules")
      setRules(res.data)
    } catch (err: any) {
      toast.error(err.message || "Failed to load SLA rules")
    } finally {
      setLoading(false)
    }
  }

  async function saveRule(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await apiClient.post("/admin/sla-rules", { ...form, active: true })
      toast.success("SLA rule saved")
      await fetchRules()
    } catch (err: any) {
      toast.error(err.message || "Failed to save SLA rule")
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">SLA Rules</h2>
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-semibold text-surface-text">SLA Rules</h2>
      <form onSubmit={saveRule} className="bg-white p-4 rounded-lg border border-surface-border grid grid-cols-3 gap-4">
        <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} className="px-3 py-2 border rounded-md">
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <input type="number" value={form.triage_hours} onChange={(e) => setForm({ ...form, triage_hours: Number(e.target.value) })} placeholder="Triage hours" className="px-3 py-2 border rounded-md" required />
        <input type="number" value={form.decision_hours} onChange={(e) => setForm({ ...form, decision_hours: Number(e.target.value) })} placeholder="Decision hours" className="px-3 py-2 border rounded-md" required />
        <button type="submit" disabled={submitting} className="col-span-3 px-4 py-2 bg-brand-primary text-white rounded-md disabled:opacity-50">Save Rule</button>
      </form>
      <div className="bg-white rounded-lg border border-surface-border overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase"><tr><th className="px-4 py-3">Priority</th><th className="px-4 py-3">Triage</th><th className="px-4 py-3">Decision</th><th className="px-4 py-3">Active</th></tr></thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id} className="border-t border-surface-border"><td className="px-4 py-3">{r.priority}</td><td className="px-4 py-3">{r.triage_hours}h</td><td className="px-4 py-3">{r.decision_hours}h</td><td className="px-4 py-3">{r.active ? "Yes" : "No"}</td></tr>
            ))}
          </tbody>
        </table>
        {rules.length === 0 && (
          <div className="p-6 text-center text-surface-muted text-sm">No SLA rules found.</div>
        )}
      </div>
    </div>
  )
}
