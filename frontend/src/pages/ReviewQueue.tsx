import { useEffect, useRef, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { isAdmin, isManager, isRecruiter } from "../lib/auth"
import { Skeleton } from "../components/Skeleton"
import {
  CheckCircle2,
  XCircle,
  ArrowRightCircle,
  Edit3,
  ShieldAlert,
  Clock,
  User,
  Briefcase,
  AlertTriangle,
  RefreshCw,
  FileText,
} from "lucide-react"
import { CvViewerModal } from "../components/CvViewerModal"

interface Task {
  id: string
  candidate_id: string
  candidate_name?: string
  job_id: string | null
  job_title?: string
  status: string
  priority: string
  triage_deadline_at: string | null
  decision_deadline_at: string | null
  triage_reason: string | null
  manager_comment: string | null
  admin_override_reason: string | null
  created_at: string | null
}

/** Returns { label, urgent, breached } for a deadline ISO string */
function slaCountdown(deadline: string | null): { label: string; urgent: boolean; breached: boolean } {
  if (!deadline) return { label: "—", urgent: false, breached: false }
  const diff = new Date(deadline).getTime() - Date.now()
  if (diff <= 0) return { label: "BREACHED", urgent: true, breached: true }
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  const urgent = diff < 4 * 3_600_000 // < 4 hours remaining
  return { label: `${h}h ${m}m`, urgent, breached: false }
}

export function ReviewQueue() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<Record<string, boolean>>({})
  const [reason, setReason] = useState<Record<string, string>>({})
  const [selectedCv, setSelectedCv] = useState<{ id: string; name?: string } | null>(null)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [, setTick] = useState(0)
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Update SLA countdowns every 30 s
  useEffect(() => {
    tickRef.current = setInterval(() => setTick((t) => t + 1), 30_000)
    return () => {
      if (tickRef.current) clearInterval(tickRef.current)
    }
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
      toast.success(`Action "${action.replace(/_/g, " ")}" recorded!`)
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
    if (!reasonText.trim()) {
      toast.error("Please enter an override reason in the comment box")
      return
    }

    const originalTasks = [...tasks]
    setActing((a) => ({ ...a, [taskId]: true }))
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: "pending_manager_review" } : t))
    )

    try {
      await apiClient.post("/review-queue/admin-override", { task_id: taskId, reason: reasonText }, { silent: true })
      toast.success("Admin override applied successfully")
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
      toast.success(`Priority updated to ${priority}`)
      await fetchTasks()
    } catch (err: any) {
      toast.error(err.message || "Failed to update priority")
      setTasks(originalTasks)
    } finally {
      setActing((a) => ({ ...a, [taskId]: false }))
    }
  }

  const activeDeadline = (t: Task) => {
    const s = (t.status || "").toLowerCase()
    return s.includes("triage") ? t.triage_deadline_at : t.decision_deadline_at
  }

  if (loading && tasks.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">Review Queue</h2>
        <div className="bg-white rounded-xl border border-surface-border p-4 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-heading font-bold text-surface-text tracking-tight">Human Review Queue (T5)</h2>
          <p className="text-sm text-surface-muted">
            Multi-stage approval gate with recruiter triage, manager decisioning, SLA countdowns, and administrative override.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchTasks()}
            placeholder="Search candidate name or ID…"
            className="px-3 py-1.5 border border-surface-border rounded-lg text-sm bg-white"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-surface-border rounded-lg text-sm bg-white"
          >
            <option value="">All Statuses</option>
            <option value="pending_triage">Pending Triage</option>
            <option value="pending_manager_review">Pending Manager Review</option>
            <option value="escalated_triage">Escalated (Triage)</option>
            <option value="escalated_manager">Escalated (Manager)</option>
            <option value="approved">Approved</option>
            <option value="rejected_at_triage">Rejected at Triage</option>
            <option value="rejected_by_manager">Rejected by Manager</option>
            <option value="edited_and_approved">Edited & Approved</option>
          </select>
          <button
            onClick={fetchTasks}
            className="px-3 py-1.5 text-sm bg-brand-primary hover:bg-brand-primary/90 text-white font-medium rounded-lg flex items-center gap-1.5 transition shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-surface-border shadow-xs overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase text-xs font-semibold">
            <tr>
              <th className="px-4 py-3">Task / Ref</th>
              <th className="px-4 py-3">Candidate Applicant</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">SLA Deadline</th>
              <th className="px-4 py-3 min-w-[200px]">Reviewer Note / Comment</th>
              <th className="px-4 py-3 text-right min-w-[240px]">Available Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {tasks.map((t) => {
              const normStatus = (t.status || "").toLowerCase()
              const isEscalated = normStatus.includes("escalated")
              const sla = slaCountdown(activeDeadline(t))
              const isTriageStage = normStatus === "pending_triage" || normStatus === "escalated_triage"
              const isManagerStage = normStatus === "pending_manager_review" || normStatus === "escalated_manager"
              const isTerminal = normStatus === "approved" || normStatus === "rejected_at_triage" || normStatus === "rejected_by_manager" || normStatus === "edited_and_approved"
              const isBusy = acting[t.id]

              return (
                <tr
                  key={t.id}
                  className={`hover:bg-surface-page/40 transition ${isEscalated ? "bg-red-50/50" : ""}`}
                >
                  {/* Task ID + Escalation Badge */}
                  <td className="px-4 py-3.5 align-top">
                    <div className="font-mono text-xs text-surface-text font-semibold">
                      #{t.id.slice(0, 8)}
                    </div>
                    {isEscalated && (
                      <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded text-[11px] bg-red-100 text-red-800 font-bold animate-pulse">
                        <AlertTriangle className="w-3 h-3 text-red-600" /> ESCALATED
                      </span>
                    )}
                  </td>

                  {/* Candidate Name & Role */}
                  <td className="px-4 py-3.5 align-top">
                    <div className="font-semibold text-surface-text flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-brand-primary" />
                      {t.candidate_name || "Candidate Applicant"}
                    </div>
                    <div className="text-xs text-surface-muted font-mono mt-0.5 flex items-center gap-1">
                      <Briefcase className="w-3 h-3" />
                      {t.job_title || "General Candidate"}
                    </div>
                    <div className="text-[11px] text-surface-muted/70 font-mono">
                      ID: {t.candidate_id.slice(0, 8)}
                    </div>
                    <button
                      id={`btn-view-cv-${t.id.slice(0, 8)}`}
                      onClick={() => setSelectedCv({ id: t.candidate_id, name: t.candidate_name })}
                      className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-brand-primary border border-brand-primary/30 rounded-md transition shadow-2xs"
                      title="View original candidate CV file"
                    >
                      <FileText className="w-3.5 h-3.5" /> View Original CV
                    </button>
                  </td>

                  {/* Status Badge */}
                  <td className="px-4 py-3.5 align-top">
                    <span className={statusBadgeClass(normStatus)}>
                      {normStatus.replace(/_/g, " ")}
                    </span>
                  </td>

                  {/* Priority Select */}
                  <td className="px-4 py-3.5 align-top">
                    {isAdmin() || isRecruiter() ? (
                      <select
                        value={(t.priority || "MEDIUM").toUpperCase()}
                        disabled={isBusy}
                        onChange={(e) => updatePriority(t.id, e.target.value)}
                        className="px-2 py-1 border border-surface-border rounded-md text-xs bg-white font-semibold shadow-xs"
                      >
                        <option value="HIGH">HIGH</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="LOW">LOW</option>
                      </select>
                    ) : (
                      <span className={priorityBadgeClass(t.priority)}>{t.priority}</span>
                    )}
                  </td>

                  {/* SLA Countdown Timer */}
                  <td className="px-4 py-3.5 align-top">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-surface-muted" />
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                          sla.breached
                            ? "bg-red-100 text-red-800"
                            : sla.urgent
                            ? "bg-amber-100 text-amber-800 animate-pulse"
                            : "bg-emerald-100 text-emerald-800"
                        }`}
                      >
                        {sla.label}
                      </span>
                    </div>
                  </td>

                  {/* Note / Comment */}
                  <td className="px-4 py-3.5 align-top">
                    <input
                      value={reason[t.id] ?? (t.manager_comment || t.triage_reason || "")}
                      disabled={isBusy || isTerminal}
                      onChange={(e) => setReason((r) => ({ ...r, [t.id]: e.target.value }))}
                      placeholder={isTerminal ? "Decision finalized" : "Add rationale or feedback…"}
                      className="w-full px-2.5 py-1 border border-surface-border rounded-lg text-xs bg-white focus:ring-1 focus:ring-brand-primary"
                    />
                  </td>

                  {/* Actions Column */}
                  <td className="px-4 py-3.5 align-top text-right space-x-1.5 whitespace-nowrap">
                    {/* Recruiter / Admin actions for Triage */}
                    {(isRecruiter() || isAdmin()) && isTriageStage && (
                      <>
                        <button
                          id={`btn-forward-${t.id.slice(0, 8)}`}
                          disabled={isBusy}
                          onClick={() => act(t.id, "forward_to_manager")}
                          title="Forward candidate to Hiring Manager review"
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-brand-primary hover:bg-brand-primary/90 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                        >
                          <ArrowRightCircle className="w-3.5 h-3.5" /> Forward
                        </button>
                        <button
                          id={`btn-reject-triage-${t.id.slice(0, 8)}`}
                          disabled={isBusy}
                          onClick={() => act(t.id, "reject_at_triage")}
                          title="Reject candidate at triage"
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-red-600 hover:bg-red-700 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Reject
                        </button>
                      </>
                    )}

                    {/* Manager / Admin actions for Decision */}
                    {(isManager() || isAdmin()) && isManagerStage && (
                      <>
                        <button
                          id={`btn-approve-${t.id.slice(0, 8)}`}
                          disabled={isBusy}
                          onClick={() => act(t.id, "approve")}
                          title="Approve candidate for shortlist"
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Approve
                        </button>
                        <button
                          id={`btn-reject-mgr-${t.id.slice(0, 8)}`}
                          disabled={isBusy}
                          onClick={() => act(t.id, "reject")}
                          title="Reject candidate"
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-red-600 hover:bg-red-700 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Reject
                        </button>
                        <button
                          id={`btn-edit-approve-${t.id.slice(0, 8)}`}
                          disabled={isBusy}
                          onClick={() => act(t.id, "edit_and_approve")}
                          title="Edit with comment and approve"
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                        >
                          <Edit3 className="w-3.5 h-3.5" /> Edit & Approve
                        </button>
                      </>
                    )}

                    {/* Admin Override Action */}
                    {isAdmin() && (
                      <button
                        id={`btn-override-${t.id.slice(0, 8)}`}
                        disabled={isBusy}
                        onClick={() => override(t.id)}
                        title="Admin override to advance or reset task status"
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                      >
                        <ShieldAlert className="w-3.5 h-3.5" /> Override
                      </button>
                    )}

                    {isTerminal && (
                      <span className="text-xs text-surface-muted italic pr-2">Decision Logged</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {tasks.length === 0 && (
          <div className="p-8 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <p className="text-sm font-semibold text-surface-text">No pending review tasks in the queue</p>
            <p className="text-xs text-surface-muted">All candidate applications have been processed or matched the filter.</p>
          </div>
        )}
      </div>

      {/* Original CV Viewer Modal */}
      <CvViewerModal
        candidateId={selectedCv?.id || null}
        candidateName={selectedCv?.name}
        isOpen={!!selectedCv}
        onClose={() => setSelectedCv(null)}
      />
    </div>
  )
}

function deriveOptimisticStatus(action: string): string {
  switch (action) {
    case "forward_to_manager": return "pending_manager_review"
    case "reject_at_triage": return "rejected_at_triage"
    case "approve": return "approved"
    case "reject": return "rejected_by_manager"
    case "edit_and_approve": return "edited_and_approved"
    default: return "escalated_manager"
  }
}

function statusBadgeClass(status: string): string {
  const base = "px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize whitespace-nowrap "
  switch (status.toLowerCase()) {
    case "pending_triage": return base + "bg-amber-100 text-amber-800"
    case "pending_manager_review": return base + "bg-blue-100 text-blue-800"
    case "approved":
    case "edited_and_approved": return base + "bg-emerald-100 text-emerald-800"
    case "rejected_at_triage":
    case "rejected_by_manager": return base + "bg-red-100 text-red-800"
    case "escalated_triage":
    case "escalated_manager": return base + "bg-red-200 text-red-900 font-bold ring-1 ring-red-400"
    default: return base + "bg-gray-100 text-gray-700"
  }
}

function priorityBadgeClass(priority: string): string {
  const base = "px-2.5 py-0.5 rounded-full text-xs font-semibold "
  switch ((priority || "MEDIUM").toUpperCase()) {
    case "HIGH": return base + "bg-red-100 text-red-800 font-bold"
    case "MEDIUM": return base + "bg-yellow-100 text-yellow-800"
    case "LOW": return base + "bg-green-100 text-green-800"
    default: return base + "bg-gray-100 text-gray-700"
  }
}
