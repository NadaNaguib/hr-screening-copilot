import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { Skeleton } from "../components/Skeleton"

interface Stats {
  total_tasks: number
  triage_completed: number
  triage_forwarded: number
  triage_rejected: number
  manager_decisions: number
  manager_approved: number
  manager_rejected: number
  manager_edited_approved: number
  escalated: number
}

export function ReviewerStats() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.get("/reviewer-stats", { silent: true })
      .then((r) => setStats(r.data))
      .catch((e) => toast.error(e.message || "Failed to load stats"))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">Reviewer Stats</h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}
        </div>
      </div>
    )
  }

  if (!stats) return null

  const cards = [
    { label: "Total Tasks", value: stats.total_tasks, color: "text-brand-primary" },
    { label: "Triage Completed", value: stats.triage_completed, color: "text-blue-600" },
    { label: "Forwarded to Manager", value: stats.triage_forwarded, color: "text-brand-accent" },
    { label: "Rejected at Triage", value: stats.triage_rejected, color: "text-red-500" },
    { label: "Manager Decisions", value: stats.manager_decisions, color: "text-blue-600" },
    { label: "Approved", value: stats.manager_approved, color: "text-green-600" },
    { label: "Rejected by Manager", value: stats.manager_rejected, color: "text-red-500" },
    { label: "Escalated", value: stats.escalated, color: "text-yellow-600" },
  ]

  const approvalRate = stats.manager_decisions > 0
    ? Math.round((stats.manager_approved / stats.manager_decisions) * 100)
    : 0

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Reviewer Stats</h2>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-lg border border-surface-border p-4 flex flex-col gap-1">
            <span className="text-xs text-surface-muted uppercase tracking-wide">{c.label}</span>
            <span className={`text-3xl font-bold ${c.color}`}>{c.value}</span>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-surface-border p-6">
        <h3 className="text-sm font-semibold text-surface-muted uppercase mb-4">Approval Rate</h3>
        <div className="flex items-center gap-4">
          <div className="flex-1 bg-surface-page rounded-full h-4 overflow-hidden">
            <div
              className="h-4 rounded-full bg-green-500 transition-all duration-700"
              style={{ width: `${approvalRate}%` }}
            />
          </div>
          <span className="text-2xl font-bold text-green-600">{approvalRate}%</span>
        </div>
        <p className="text-xs text-surface-muted mt-2">
          {stats.manager_approved} approved out of {stats.manager_decisions} manager decisions
        </p>
      </div>

      {stats.escalated > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-red-700">{stats.escalated} task(s) currently escalated</p>
            <p className="text-xs text-red-600">These have breached their SLA — immediate attention required.</p>
          </div>
        </div>
      )}
    </div>
  )
}
