import { useEffect, useState } from "react"
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
  ESCALATED_MANAGER: "ESCALATED_MANAGER",
} as const

interface Task {
  id: string
  candidate_id: string
  job_id: string | null
  status: string
  priority: string
  triage_reason: string | null
  manager_comment: string | null
  admin_override_reason: string | null
}

export function ReviewQueue() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<Record<string, boolean>>({})
  const [reason, setReason] = useState<Record<string, string>>({})

  useEffect(() => {
    fetchTasks()
  }, [])

  async function fetchTasks() {
    setLoading(true)
    try {
      const res = await apiClient.get("/review-queue", { silent: true })
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

    const endpoint = action.startsWith("forward") || action === "reject_at_triage" ? "/review-queue/triage" : "/review-queue/decide"
    const reasonText = reason[taskId] || ""

    const originalTasks = [...tasks]
    const nextStatus = deriveOptimisticStatus(action)
    setActing((a) => ({ ...a, [taskId]: true }))
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: nextStatus } : t))
    )

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
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return

    const reasonText = reason[taskId] || ""
    if (!reasonText.trim()) {
      toast.error("Override reason is required")
      return
    }

    const originalTasks = [...tasks]
    setActing((a) => ({ ...a, [taskId]: true }))
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId ? { ...t, status: STATUS.PENDING_MANAGER_REVIEW, admin_override_reason: reasonText } : t
      )
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
      <h2 className="text-2xl font-heading font-semibold text-surface-text">Review Queue</h2>
      <div className="bg-white rounded-lg border border-surface-border overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase">
            <tr>
              <th className="px-4 py-3">Task ID</th>
              <th className="px-4 py-3">Candidate</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Reason / Comment</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id} className="border-t border-surface-border">
                <td className="px-4 py-3 font-mono text-xs">{t.id.slice(0, 8)}</td>
                <td className="px-4 py-3">{t.candidate_id.slice(0, 8)}</td>
                <td className="px-4 py-3">
                  <span className={statusBadgeClass(t.status)}>{t.status}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={priorityBadgeClass(t.priority)}>{t.priority}</span>
                </td>
                <td className="px-4 py-3">
                  <input
                    value={reason[t.id] || ""}
                    disabled={acting[t.id]}
                    onChange={(e) => setReason((r) => ({ ...r, [t.id]: e.target.value }))}
                    placeholder="Reason..."
                    className="w-full px-2 py-1 border border-surface-border rounded-md text-xs"
                  />
                </td>
                <td className="px-4 py-3 space-x-1">
                  {isRecruiter() && t.status === STATUS.PENDING_TRIAGE && (
                    <>
                      <button disabled={acting[t.id]} onClick={() => act(t.id, "forward_to_manager")} className="px-2 py-1 text-xs bg-brand-primary text-white rounded-md disabled:opacity-50">Forward</button>
                      <button disabled={acting[t.id]} onClick={() => act(t.id, "reject_at_triage")} className="px-2 py-1 text-xs bg-semantic-danger text-white rounded-md disabled:opacity-50">Reject</button>
                    </>
                  )}
                  {isManager() && t.status === STATUS.PENDING_MANAGER_REVIEW && (
                    <>
                      <button disabled={acting[t.id]} onClick={() => act(t.id, "approve")} className="px-2 py-1 text-xs bg-semantic-success text-white rounded-md disabled:opacity-50">Approve</button>
                      <button disabled={acting[t.id]} onClick={() => act(t.id, "reject")} className="px-2 py-1 text-xs bg-semantic-danger text-white rounded-md disabled:opacity-50">Reject</button>
                      <button disabled={acting[t.id]} onClick={() => act(t.id, "edit_and_approve")} className="px-2 py-1 text-xs bg-brand-accent text-white rounded-md disabled:opacity-50">Edit & Approve</button>
                    </>
                  )}
                  {isAdmin() && (t.status === STATUS.PENDING_TRIAGE || t.status === STATUS.PENDING_MANAGER_REVIEW) && (
                    <button disabled={acting[t.id]} onClick={() => override(t.id)} className="px-2 py-1 text-xs bg-semantic-warning text-white rounded-md disabled:opacity-50">Override</button>
                  )}
                </td>
              </tr>
            ))}
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
    case "forward_to_manager":
      return STATUS.PENDING_MANAGER_REVIEW
    case "reject_at_triage":
      return STATUS.REJECTED_AT_TRIAGE
    case "approve":
      return STATUS.APPROVED
    case "reject":
      return STATUS.REJECTED_BY_MANAGER
    case "edit_and_approve":
      return STATUS.EDITED_AND_APPROVED
    default:
      return STATUS.ESCALATED_MANAGER
  }
}

function statusBadgeClass(status: string): string {
  const base = "px-2 py-1 rounded-full text-xs font-medium "
  switch (status) {
    case STATUS.PENDING_TRIAGE:
      return base + "bg-semantic-warning/10 text-semantic-warning"
    case STATUS.PENDING_MANAGER_REVIEW:
      return base + "bg-semantic-info/10 text-semantic-info"
    case STATUS.APPROVED:
    case STATUS.EDITED_AND_APPROVED:
      return base + "bg-semantic-success/10 text-semantic-success"
    case STATUS.REJECTED_AT_TRIAGE:
    case STATUS.REJECTED_BY_MANAGER:
      return base + "bg-semantic-danger/10 text-semantic-danger"
    default:
      return base + "bg-surface-border text-surface-muted"
  }
}

function priorityBadgeClass(priority: string): string {
  const base = "px-2 py-1 rounded-full text-xs font-medium "
  switch (priority.toUpperCase()) {
    case "HIGH":
      return base + "bg-semantic-danger/10 text-semantic-danger"
    case "MEDIUM":
      return base + "bg-semantic-warning/10 text-semantic-warning"
    case "LOW":
      return base + "bg-semantic-success/10 text-semantic-success"
    default:
      return base + "bg-surface-border text-surface-muted"
  }
}
