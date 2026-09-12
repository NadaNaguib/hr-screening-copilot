import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { Pencil, Trash2 } from "lucide-react"
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

const PRIORITY_PRESETS = ["HIGH", "MEDIUM", "LOW"]
const CUSTOM_PRIORITY = "__custom__"

export function SettingsSlaRules() {
  const [rules, setRules] = useState<SLARule[]>([])
  const [form, setForm] = useState({ priority: "MEDIUM", triage_hours: 48, decision_hours: 48 })
  const [customPriority, setCustomPriority] = useState("")
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingJobId, setEditingJobId] = useState<string | null>(null)

  const isCustom = !PRIORITY_PRESETS.includes(form.priority)
  const isEditing = editingId !== null

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

  function resetForm() {
    setEditingId(null)
    setEditingJobId(null)
    setCustomPriority("")
    setForm({ priority: "MEDIUM", triage_hours: 48, decision_hours: 48 })
  }

  function startEdit(rule: SLARule) {
    const priority = (rule.priority || "MEDIUM").toUpperCase()
    setEditingId(rule.id)
    setEditingJobId(rule.job_id)
    if (PRIORITY_PRESETS.includes(priority)) {
      setCustomPriority("")
      setForm({ priority, triage_hours: rule.triage_hours, decision_hours: rule.decision_hours })
    } else {
      setCustomPriority(priority)
      setForm({
        priority: CUSTOM_PRIORITY,
        triage_hours: rule.triage_hours,
        decision_hours: rule.decision_hours,
      })
    }
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  async function saveRule(e: React.FormEvent) {
    e.preventDefault()
    const priority = (isCustom ? customPriority : form.priority).trim().toUpperCase()
    if (!priority) {
      toast.error("Please enter a priority name")
      return
    }
    setSubmitting(true)
    try {
      await apiClient.post("/admin/sla-rules", {
        id: editingId ?? undefined,
        job_id: editingJobId ?? undefined,
        priority,
        triage_hours: form.triage_hours,
        decision_hours: form.decision_hours,
        active: true,
      })
      toast.success(isEditing ? "SLA rule updated" : "SLA rule created")
      resetForm()
      await fetchRules()
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || "Failed to save SLA rule")
    } finally {
      setSubmitting(false)
    }
  }

  async function deleteRule(rule: SLARule) {
    const scope = rule.job_id ? `job ${rule.job_id.slice(0, 8)}…` : "the global default"
    if (!confirm(`Delete the ${rule.priority.toUpperCase()} SLA rule for ${scope}? This cannot be undone.`)) {
      return
    }
    setDeletingId(rule.id)
    try {
      await apiClient.delete(`/admin/sla-rules/${rule.id}`)
      toast.success("SLA rule deleted")
      await fetchRules()
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || "Failed to delete SLA rule")
    } finally {
      setDeletingId(null)
    }
  }

  function formatDuration(hours: number) {
    if (hours < 24) return `${hours} hrs`
    const days = (hours / 24).toFixed(hours % 24 === 0 ? 0 : 1)
    return `${hours} hrs (${days} day${Number(days) > 1 ? "s" : ""})`
  }

  // Badge palette: LOW=green, MEDIUM=amber, HIGH=rose, everything else (custom
  // priorities such as CRITICAL) = purple. No enum fallback — the label is always
  // the exact `priority` string returned by the API.
  const PRIORITY_BADGE_STYLES: Record<string, string> = {
    LOW: "bg-emerald-100 text-emerald-800",
    MEDIUM: "bg-amber-100 text-amber-800",
    HIGH: "bg-rose-100 text-rose-800",
  }
  const PRIORITY_BADGE_CUSTOM = "bg-purple-100 text-purple-800"

  function getPriorityBadge(priority: string) {
    const label = (priority || "").trim() || "—"
    const palette =
      PRIORITY_BADGE_STYLES[label.toUpperCase()] ?? PRIORITY_BADGE_CUSTOM
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${palette}`}
      >
        {label}
      </span>
    )
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">SLA & Escalation Rules</h2>
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Service Level Agreement (SLA) Rules</h2>
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
            Maximum hours allotted from initial CV submission to recruiter screening decision. If this time expires, the task is automatically forwarded to the Hiring Manager for review.
          </p>
        </div>
        <div className="space-y-1">
          <div className="font-semibold text-blue-950 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-indigo-600"></span>
            Decision Deadline (Stage 2 · Hiring Manager)
          </div>
          <p className="text-xs text-blue-800 leading-relaxed">
            Maximum hours allotted after recruiter triage for the Hiring Manager to finalize approval, rejection, or feedback. If expired, the task is automatically approved and its timer is frozen.
          </p>
        </div>
      </div>

      {/* Configure rule form */}
      <div className="bg-white p-5 rounded-xl border border-surface-border shadow-sm">
        <h3 className="text-base font-semibold text-surface-text mb-4">
          {isEditing ? "Update SLA Rule" : "Set SLA Rule"}
          {isEditing && (
            <span className="ml-2 text-xs font-mono text-surface-muted">
              editing #{editingId?.slice(0, 8)}
            </span>
          )}
        </h3>
        <form onSubmit={saveRule} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1.5">Candidate Priority</label>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            >
              <option value="HIGH">High Priority (Urgent / Critical roles)</option>
              <option value="MEDIUM">Medium Priority (Standard hires)</option>
              <option value="LOW">Low Priority (Pipeline pooling)</option>
              <option value={CUSTOM_PRIORITY}>Custom priority…</option>
            </select>
            {isCustom && (
              <input
                value={customPriority}
                onChange={(e) => setCustomPriority(e.target.value)}
                placeholder="e.g. CRITICAL"
                className="mt-2 w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white uppercase focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
                required
              />
            )}
            <span className="text-[11px] text-surface-muted mt-1 block">
              Saved as{" "}
              <span className="font-mono font-semibold">
                {(isCustom ? customPriority : form.priority).toUpperCase() || "—"}
              </span>
            </span>
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

          <div className="sm:col-span-3 flex justify-end gap-2 pt-2">
            {isEditing && (
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2.5 border border-surface-border text-surface-text text-sm font-medium rounded-lg hover:bg-surface-page transition"
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 bg-brand-primary hover:bg-brand-primary/90 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition shadow-sm"
            >
              {submitting ? "Saving..." : isEditing ? "Update Rule" : "Create Rule"}
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
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {rules.map((r) => (
                <tr
                  key={r.id}
                  className={`transition hover:bg-surface-page/50 ${
                    editingId === r.id ? "bg-amber-50/60" : ""
                  }`}
                >
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
                  <td className="px-5 py-3.5 text-right whitespace-nowrap space-x-1.5">
                    <button
                      type="button"
                      onClick={() => startEdit(r)}
                      title="Edit this SLA rule"
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-brand-primary hover:bg-indigo-50 border border-brand-primary/30 rounded-md transition"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteRule(r)}
                      disabled={deletingId === r.id}
                      title="Delete this SLA rule"
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-red-600 hover:text-red-800 hover:bg-red-50 border border-red-200 rounded-md transition disabled:opacity-50"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      {deletingId === r.id ? "Deleting…" : "Delete"}
                    </button>
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
