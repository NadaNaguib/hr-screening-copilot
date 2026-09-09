import { useEffect, useRef, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { isAdmin, isManager, isRecruiter } from "../lib/auth"
import { Skeleton } from "../components/Skeleton"

const STATUS = {
  PENDING_TRIAGE: "PENDING_TRIAGE",
  PENDING_MANAGER_REVIEW: "PENDING_MANAGER_REVIEW",
  REJECTED_AT_TRIAGE: "REJECTED_AT_TRIAGE",
  APPROVED: "APPROVED",
  REJECTED_BY_MANAGER: "REJECTED_BY_MANAGER",
  EDITED_AND_APPROVED: "EDITED_AND_APPROVED",
  ESCALATED_TRIAGE: "ESCALATED_TRIAGE",
  ESCALATED_MANAGER: "ESCALATED_MANAGER",
} as const

interface Task {
  id: string
  candidate_id: string
  job_id: string | null
  status: string
  priority: string
  triage_deadline_at: string | null
  decision_deadline_at: string | null
  triage_reason: string | null
  manager_comment: string | null
  admin_override_reason: string | null
  created_at: string | null
}

/** Returns { label, urgent } for a deadline ISO string */
function slaCountdown(deadline: string | null): { label: string; urgent: boolean; breached: boolean } {
  if (!deadline) return { label: "—", urgent: false, breached: false }
  const diff = new Date(deadline).getTime() - Date.now()
  if (diff <= 0) return { label: "BREACHED", urgent: true, breached: true }
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  const urgent = diff < 4 * 3_600_000 // <4 h left
  return { label: `${h}h ${m}m`, urgent, breached: false }
}

export function ReviewQueue() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<Record<string, boolean>>({})
  const [reason, setReason] = useState<Record<string, string>>({})
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [tick, setTick] = useState(0)
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Update SLA countdowns every 30 s
  useEffect(() => {
    tickRef.current = setInterval(() => setTick((t) => t + 1), 30_000)
    return () => { if (tickRef.current) clearInterval(tickRef.current) }
  }, [])

  useEffect(() => {
    fetchTasks()
  }, [statusFilter])

  async function fetchTasks() {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (statusFilter) params["status"] = statusFilter
      if (search) params["search"] = search
      const res = await apiClient.get("/review-queue", { params, silent: true })
      setTasks(res.data)
    } catch (err: any) {
      toast.error(err.message || "Failed to load review queue")
    } finally {
      setLoading(false)
    }
  }

  async function act(taskId: string, action: string) {
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return

    const endpoint =
      action === "forward_to_manager" || action === "reject_at_triage"
        ? "/review-queue/triage"
        : "/review-queue/decide"
    const reasonText = reason[taskId] || ""

    const originalTasks = [...tasks]
    const nextStatus = deriveOptimisticStatus(action)
    setActing((a) => ({ ...a, [taskId]: true }))
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: nextStatus } : t)))

    try {
      await apiClient.post(endpoint, { task_id: taskId, action, reason: reasonText }, { silent: true })
      toast.success("Action recorded")
      await fetchTasks()
    } catch (err: any) {
      toast.error(err.message || "Action failed")
      setTasks(originalTasks)
    } finally {
      setActing((a) => ({ ...a, [taskId]: false }))
    }
  }

  async function override(taskId: string) {
    const reasonText = reason[taskId] || ""
    if (!reasonText.trim()) { toast.error("Override reason is required"); return }

    const originalTasks = [...tasks]
    setActing((a) => ({ ...a, [taskId]: true }))
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: STATUS.PENDING_MANAGER_REVIEW } : t))
    )

    try {
      await apiClient.post("/review-queue/admin-override", { task_id: taskId, reason: reasonText }, { silent: true })
      toast.success("Override applied")
      await fetchTasks()
    } catch (err: any) {
      toast.error(err.message || "Override failed")
      setTasks(originalTasks)
    } finally {
      setActing((a) => ({ ...a, [taskId]: false }))
    }
  }

  async function updatePriority(taskId: string, priority: string) {
    const task = tasks.find((t) => t.id === taskId)
    if (!task || task.priority === priority) return

    const originalTasks = [...tasks]
    setActing((a) => ({ ...a, [taskId]: true }))
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, priority } : t)))

    try {
      await apiClient.post("/review-queue/update-priority", { task_id: taskId, priority }, { silent: true })
      toast.success("Priority updated")
      await fetchTasks()
    } catch (err: any) {
      toast.error(err.message || "Failed to update priority")
      setTasks(originalTasks)
    } finally {
      setActing((a) => ({ ...a, [taskId]: false }))
    }
  }

  const activeDeadline = (t: Task) =>
    t.status === STATUS.PENDING_TRIAGE || t.status === STATUS.ESCALATED_TRIAGE
      ? t.triage_deadline_at
      : t.decision_deadline_at

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">Review Queue</h2>
        <div className="bg-white rounded-lg border border-surface-border p-4 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">Review Queue</h2>
        <div className="flex gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchTasks()}
            placeholder="Search candidate ID…"
            className="px-3 py-1.5 border border-surface-border rounded-md text-sm"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-surface-border rounded-md text-sm bg-white"
          >
            <option value="">All statuses</option>
            <option value="PENDING_TRIAGE">Pending Triage</option>
            <option value="PENDING_MANAGER_REVIEW">Pending Manager</option>
            <option value="ESCALATED_TRIAGE">Escalated (Triage)</option>
            <option value="ESCALATED_MANAGER">Escalated (Manager)</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED_AT_TRIAGE">Rejected at Triage</option>
            <option value="REJECTED_BY_MANAGER">Rejected by Manager</option>
          </select>
          <button
            onClick={fetchTasks}
            className="px-3 py-1.5 text-sm bg-brand-primary text-white rounded-md"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-surface-border overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase text-xs">
            <tr>
              <th className="px-4 py-3">Task</th>
              <th className="px-4 py-3">Candidate</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">SLA Deadline</th>
              <th className="px-4 py-3">Reason / Comment</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => {
              const sla = slaCountdown(activeDeadline(t))
              const isEscalated = t.status === STATUS.ESCALATED_TRIAGE || t.status === STATUS.ESCALATED_MANAGER
              return (
                <tr
                  key={t.id}
                  className={`border-t border-surface-border ${isEscalated ? "bg-red-50" : ""}`}
                >
                  <td className="px-4 py-3 font-mono text-xs">
                    {t.id.slice(0, 8)}
                    {isEscalated && (
                      <span className="ml-1 px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-700 font-semibold animate-pulse">
                        ⚠ ESCALATED
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{t.candidate_id.slice(0, 8)}</td>
                  <td className="px-4 py-3">
                    <span className={statusBadgeClass(t.status)}>{t.status.replace(/_/g, " ")}</span>
                  </td>
                  <td className="px-4 py-3">
                    {isAdmin() || isRecruiter() ? (
                      <select
                        value={t.priority}
                        disabled={acting[t.id]}
                        onChange={(e) => updatePriority(t.id, e.target.value)}
                        className="px-2 py-1 border border-surface-border rounded-md text-xs bg-white"
                      >
                        <option value="HIGH">HIGH</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="LOW">LOW</option>
                      </select>
                    ) : (
                      <span className={priorityBadgeClass(t.priority)}>{t.priority}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-mono font-medium ${
                        sla.breached
                          ? "bg-red-100 text-red-700"
                          : sla.urgent
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-green-50 text-green-700"
                      }`}
                    >
                      {sla.label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <input
                      value={reason[t.id] || ""}
                      disabled={acting[t.id]}
                      onChange={(e) => setReason((r) => ({ ...r, [t.id]: e.target.value }))}
                      placeholder="Reason / comment…"
                      className="w-full px-2 py-1 border border-surface-border rounded-md text-xs"
                    />
                  </td>
                  <td className="px-4 py-3 space-x-1 whitespace-nowrap">
                    {(isRecruiter() || isAdmin()) && t.status === STATUS.PENDING_TRIAGE && (
                      <>
                        <button
                          id={`btn-forward-${t.id.slice(0, 8)}`}
                          disabled={acting[t.id]}
                          onClick={() => act(t.id, "forward_to_manager")}
                          className="px-2 py-1 text-xs bg-brand-primary text-white rounded-md disabled:opacity-50"
                        >
                          Forward
                        </button>
                        <button
                          id={`btn-reject-triage-${t.id.slice(0, 8)}`}
                          disabled={acting[t.id]}
                          onClick={() => act(t.id, "reject_at_triage")}
                          className="px-2 py-1 text-xs bg-semantic-danger text-white rounded-md disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </>
                    )}
                    {(isManager() || isAdmin()) && t.status === STATUS.PENDING_MANAGER_REVIEW && (
                      <>
                        <button
                          id={`btn-approve-${t.id.slice(0, 8)}`}
                          disabled={acting[t.id]}
                          onClick={() => act(t.id, "approve")}
                          className="px-2 py-1 text-xs bg-semantic-success text-white rounded-md disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          id={`btn-reject-mgr-${t.id.slice(0, 8)}`}
                          disabled={acting[t.id]}
                          onClick={() => act(t.id, "reject")}
                          className="px-2 py-1 text-xs bg-semantic-danger text-white rounded-md disabled:opacity-50"
                        >
                          Reject
                        </button>
                        <button
                          id={`btn-edit-approve-${t.id.slice(0, 8)}`}
                          disabled={acting[t.id]}
                          onClick={() => act(t.id, "edit_and_approve")}
                          className="px-2 py-1 text-xs bg-brand-accent text-white rounded-md disabled:opacity-50"
                        >
                          Edit & Approve
                        </button>
                      </>
                    )}
                    {isAdmin() &&
                      (t.status === STATUS.PENDING_TRIAGE ||
                        t.status === STATUS.PENDING_MANAGER_REVIEW ||
                        t.status === STATUS.ESCALATED_TRIAGE ||
                        t.status === STATUS.ESCALATED_MANAGER) && (
                        <button
                          id={`btn-override-${t.id.slice(0, 8)}`}
                          disabled={acting[t.id]}
                          onClick={() => override(t.id)}
                          className="px-2 py-1 text-xs bg-semantic-warning text-white rounded-md disabled:opacity-50"
                        >
                          Override
                        </button>
                      )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {tasks.length === 0 && (
          <div className="p-6 text-center text-surface-muted text-sm">No tasks in the queue.</div>
        )}
      </div>
    </div>
  )
}

function deriveOptimisticStatus(action: string): string {
  switch (action) {
    case "forward_to_manager": return STATUS.PENDING_MANAGER_REVIEW
    case "reject_at_triage": return STATUS.REJECTED_AT_TRIAGE
    case "approve": return STATUS.APPROVED
    case "reject": return STATUS.REJECTED_BY_MANAGER
    case "edit_and_approve": return STATUS.EDITED_AND_APPROVED
    default: return STATUS.ESCALATED_MANAGER
  }
}

function statusBadgeClass(status: string): string {
  const base = "px-2 py-0.5 rounded-full text-xs font-medium "
  switch (status) {
    case STATUS.PENDING_TRIAGE: return base + "bg-yellow-100 text-yellow-700"
    case STATUS.PENDING_MANAGER_REVIEW: return base + "bg-blue-100 text-blue-700"
    case STATUS.APPROVED:
    case STATUS.EDITED_AND_APPROVED: return base + "bg-green-100 text-green-700"
    case STATUS.REJECTED_AT_TRIAGE:
    case STATUS.REJECTED_BY_MANAGER: return base + "bg-red-100 text-red-700"
    case STATUS.ESCALATED_TRIAGE:
    case STATUS.ESCALATED_MANAGER: return base + "bg-red-200 text-red-800 font-bold"
    default: return base + "bg-gray-100 text-gray-600"
  }
}

function priorityBadgeClass(priority: string): string {
  const base = "px-2 py-0.5 rounded-full text-xs font-medium "
  switch (priority.toUpperCase()) {
    case "HIGH": return base + "bg-red-100 text-red-700"
    case "MEDIUM": return base + "bg-yellow-100 text-yellow-700"
    case "LOW": return base + "bg-green-100 text-green-700"
    default: return base + "bg-gray-100 text-gray-600"
  }
}
