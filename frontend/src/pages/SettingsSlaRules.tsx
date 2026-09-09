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
      toast.error(err.response?.data?.message || err.message || "Failed to load SLA rules")
    } finally {
      setLoading(false)
    }
  }

  async function saveRule(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await apiClient.post("/admin/sla-rules", { ...form, active: true })
      toast.success("SLA rule saved successfully")
      await fetchRules()
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || "Failed to save SLA rule")
    } finally {
      setSubmitting(false)
    }
  }

  function formatDuration(hours: number) {
    if (hours < 24) return `${hours} hrs`
    const days = (hours / 24).toFixed(hours % 24 === 0 ? 0 : 1)
    return `${hours} hrs (${days} day${Number(days) > 1 ? "s" : ""})`
  }

  function getPriorityBadge(priority: string) {
    const p = priority.toLowerCase()
    if (p === "high") {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">HIGH Priority</span>
    }
    if (p === "medium") {
      return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">MEDIUM Priority</span>
    }
    return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">LOW Priority</span>
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">SLA & Escalation Rules</h2>
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-heading font-semibold text-surface-text">Service Level Agreement (SLA) Rules</h2>
          <p className="text-sm text-surface-muted mt-1">
            Configure automated countdown deadlines and breach escalation timers for applicant review pipelines.
          </p>
        </div>
      </div>

      {/* Metric explanation card */}
      <div className="bg-blue-50/70 border border-blue-200/80 rounded-xl p-4 text-sm text-blue-900 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1">
          <div className="font-semibold text-blue-950 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-600"></span>
            Triage Deadline (Stage 1 · HR Recruiter)
          </div>
          <p className="text-xs text-blue-800 leading-relaxed">
            Maximum hours allotted from initial CV submission to recruiter screening decision. When this time expires, the task auto-escalates to <span className="font-mono font-semibold">TRIAGE_ESCALATED</span>.
          </p>
        </div>
        <div className="space-y-1">
          <div className="font-semibold text-blue-950 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-indigo-600"></span>
            Decision Deadline (Stage 2 · Hiring Manager)
          </div>
          <p className="text-xs text-blue-800 leading-relaxed">
            Maximum hours allotted after recruiter triage for the Hiring Manager to finalize approval, rejection, or feedback. When expired, task escalates to <span className="font-mono font-semibold">DECISION_ESCALATED</span>.
          </p>
        </div>
      </div>

      {/* Configure rule form */}
      <div className="bg-white p-5 rounded-xl border border-surface-border shadow-sm">
        <h3 className="text-base font-semibold text-surface-text mb-4">Set / Update SLA Rule</h3>
        <form onSubmit={saveRule} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1.5">Candidate Priority</label>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            >
              <option value="high">High Priority (Urgent / Critical roles)</option>
              <option value="medium">Medium Priority (Standard hires)</option>
              <option value="low">Low Priority (Pipeline pooling)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1.5">
              Triage SLA (Recruiter Hours)
            </label>
            <input
              type="number"
              min={1}
              max={720}
              value={form.triage_hours}
              onChange={(e) => setForm({ ...form, triage_hours: Math.max(1, Number(e.target.value)) })}
              placeholder="e.g. 24"
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              required
            />
            <span className="text-[11px] text-surface-muted mt-1 block">
              = {formatDuration(form.triage_hours)}
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1.5">
              Decision SLA (Manager Hours)
            </label>
            <input
              type="number"
              min={1}
              max={720}
              value={form.decision_hours}
              onChange={(e) => setForm({ ...form, decision_hours: Math.max(1, Number(e.target.value)) })}
              placeholder="e.g. 48"
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              required
            />
            <span className="text-[11px] text-surface-muted mt-1 block">
              = {formatDuration(form.decision_hours)}
            </span>
          </div>

          <div className="sm:col-span-3 flex justify-end pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 bg-brand-primary hover:bg-brand-primary/90 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition shadow-sm"
            >
              {submitting ? "Saving..." : "Save SLA Configuration"}
            </button>
          </div>
        </form>
      </div>

      {/* Rules Table */}
      <div className="bg-white rounded-xl border border-surface-border shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="text-base font-semibold text-surface-text">Active SLA Rules Table</h3>
          <span className="text-xs text-surface-muted">Total: {rules.length} rule{rules.length !== 1 ? "s" : ""}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface-page text-surface-muted uppercase text-xs">
              <tr>
                <th className="px-5 py-3">Priority Level</th>
                <th className="px-5 py-3">Scope</th>
                <th className="px-5 py-3">Triage Deadline (Stage 1)</th>
                <th className="px-5 py-3">Decision Deadline (Stage 2)</th>
                <th className="px-5 py-3">Active Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {rules.map((r) => (
                <tr key={r.id} className="hover:bg-surface-page/50 transition">
                  <td className="px-5 py-3.5 font-medium text-surface-text">
                    {getPriorityBadge(r.priority)}
                  </td>
                  <td className="px-5 py-3.5 text-surface-muted text-xs">
                    {r.job_id ? `Job-specific (${r.job_id.slice(0, 8)}...)` : "Global Default (All Jobs)"}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-surface-text">
                    {formatDuration(r.triage_hours)}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-surface-text">
                    {formatDuration(r.decision_hours)}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {r.active ? "Active" : "Disabled"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rules.length === 0 && (
          <div className="p-8 text-center text-surface-muted text-sm">No SLA rules found.</div>
        )}
      </div>
    </div>
  )
}
