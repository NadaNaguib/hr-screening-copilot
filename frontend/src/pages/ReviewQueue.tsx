import { useEffect, useRef, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { isAdmin, isManager, isRecruiter } from "../lib/auth"
import { Skeleton } from "../components/Skeleton"
import {
  CheckCircle2,
  XCircle,
  ArrowRightCircle,
  Clock,
  User,
  Briefcase,
  AlertTriangle,
  Filter,
  FileText,
  ClipboardList,
  Plus,
  Trash2,
  Save,
  X,
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
  overall_score?: number | null
  triage_deadline_at: string | null
  decision_deadline_at: string | null
  sla_phase?: string
  sla_active?: boolean
  sla_deadline_at?: string | null
  sla_resolved_at?: string | null
  sla_outcome?: string | null
  triage_reason: string | null
  manager_comment: string | null
  admin_override_reason: string | null
  created_at: string | null
  probes_generated?: boolean
  interview_probes?: Probe[]
}

interface Probe {
  category: string
  question: string
}

interface JobOption {
  id: string
  title: string
}

// Status filter options, scoped by the viewer's role (recruiter sees triage +
// decision history; a manager only sees decision-stage outcomes).
const RECRUITER_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "pending_triage", label: "Pending Triage" },
  { value: "rejected_at_triage", label: "Rejected at Triage" },
  { value: "pending_manager_review", label: "Pending Manager Review" },
  { value: "approved", label: "Approved" },
  { value: "edited_and_approved", label: "Edited and Approved" },
  { value: "rejected_by_manager", label: "Rejected by Manager" },
]

const MANAGER_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "pending_manager_review", label: "Pending Manager Review" },
  { value: "approved", label: "Approved" },
  { value: "edited_and_approved", label: "Edited and Approved" },
  { value: "rejected_by_manager", label: "Rejected by Manager" },
]

function statusOptionsForRole(): { value: string; label: string }[] {
  return isManager() ? MANAGER_STATUS_OPTIONS : RECRUITER_STATUS_OPTIONS
}

function bulkOptionsForRole(): { value: string; label: string }[] {
  if (isRecruiter()) {
    return [
      { value: "forward_to_manager", label: "Forward to Manager" },
      { value: "reject_at_triage", label: "Reject at Triage" },
    ]
  }
  if (isManager()) {
    return [
      { value: "approve", label: "Approve" },
      { value: "reject", label: "Reject" },
    ]
  }
  return []
}

/**
 * Parse a backend deadline into epoch ms.
 *
 * The API emits explicit-offset ISO strings (``...+00:00``), but we defensively
 * treat a bare ``"...T12:00:00"`` (no zone) as UTC rather than local time —
 * otherwise a UTC+3 client would see a 24h window as 21h.
 */
function parseUtcMs(iso: string): number {
  const value = iso.trim()
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(value)
  return new Date(hasZone ? value : `${value}Z`).getTime()
}

/** Returns { label, urgent, breached } for a deadline ISO string */
function slaCountdown(deadline: string | null): { label: string; urgent: boolean; breached: boolean } {
  if (!deadline) return { label: "—", urgent: false, breached: false }
  const diff = parseUtcMs(deadline) - Date.now()
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
  const [probesTask, setProbesTask] = useState<Task | null>(null)
  const [probesDraft, setProbesDraft] = useState<Probe[]>([])
  const [savingProbes, setSavingProbes] = useState(false)
  const [statusFilter, setStatusFilter] = useState("")
  const [priorityFilter, setPriorityFilter] = useState("")
  const [jobFilter, setJobFilter] = useState("")
  const [jobs, setJobs] = useState<JobOption[]>([])
  const [slaPriorities, setSlaPriorities] = useState<string[]>([])
  const [selectedIds, setSelectedIds] = useState<Record<string, boolean>>({})
  const [bulkAction, setBulkAction] = useState("")
  const [bulkReason, setBulkReason] = useState("")
  const [bulkBusy, setBulkBusy] = useState(false)
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
    fetchSlaPriorities()
    fetchJobs()
    // Filters are applied explicitly via the "Update" button.
  }, [])

  async function fetchSlaPriorities() {
    try {
      const res = await apiClient.get("/admin/sla-rules/priorities", { silent: true })
      setSlaPriorities(Array.isArray(res.data) ? res.data : [])
    } catch {
      // Fall back to the canonical levels if the SLA API is unavailable.
      setSlaPriorities(["HIGH", "MEDIUM", "LOW"])
    }
  }

  async function fetchJobs() {
    try {
      const res = await apiClient.get("/jobs", { silent: true })
      setJobs(Array.isArray(res.data) ? res.data.map((j: JobOption) => ({ id: j.id, title: j.title })) : [])
    } catch {
      setJobs([])
    }
  }

  async function fetchTasks(overrides?: { status?: string; priority?: string; jobId?: string }) {
    const status = overrides?.status ?? statusFilter
    const priority = overrides?.priority ?? priorityFilter
    const jobId = overrides?.jobId ?? jobFilter
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (status) params["status"] = status
      if (priority) params["priority"] = priority
      if (jobId) params["job_id"] = jobId
      const res = await apiClient.get("/review-queue", { params, silent: true })
      setTasks(res.data)
      setSelectedIds({})
    } catch (err: any) {
      toast.error(err.message || "Failed to load review queue")
    } finally {
      setLoading(false)
    }
  }

  function clearFilters() {
    setStatusFilter("")
    setPriorityFilter("")
    setJobFilter("")
    setSelectedIds({})
    fetchTasks({ status: "", priority: "", jobId: "" })
  }

  async function act(taskId: string, action: string) {
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return

    const endpoint =
      action === "forward_to_manager" || action === "reject_at_triage"
        ? "/review-queue/triage"
        : "/review-queue/decide"
    const reasonText = (reason[taskId] || "").trim()

    // Rejecting a candidate is the ONLY action that mandates a comment. The
    // backend enforces this too (HTTP 400); we block early for instant feedback.
    if ((action === "reject" || action === "reject_at_triage") && !reasonText) {
      toast.error("A comment explaining the decision is required before rejecting a candidate.")
      return
    }

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

  const selectedCount = Object.values(selectedIds).filter(Boolean).length
  const allSelected = tasks.length > 0 && tasks.every((t) => selectedIds[t.id])

  function toggleAll() {
    if (allSelected) {
      setSelectedIds({})
    } else {
      setSelectedIds(Object.fromEntries(tasks.map((t) => [t.id, true])))
    }
  }

  function toggleOne(taskId: string) {
    setSelectedIds((prev) => ({ ...prev, [taskId]: !prev[taskId] }))
  }

  async function applyBulk() {
    const ids = Object.keys(selectedIds).filter((id) => selectedIds[id])
    if (ids.length === 0) {
      toast.error("Select at least one candidate to run a bulk action")
      return
    }
    if (!bulkAction) {
      toast.error("Choose a bulk action before applying")
      return
    }
    const isReject = bulkAction === "reject" || bulkAction === "reject_at_triage"
    if (isReject && !bulkReason.trim()) {
      // Same rule as the single-row reject — enforced again by the backend (400).
      toast.error("A comment explaining the decision is required before rejecting a candidate.")
      return
    }

    setBulkBusy(true)
    try {
      const res = await apiClient.post(
        "/review-queue/bulk",
        {
          task_ids: ids,
          action: bulkAction,
          reason: bulkReason.trim() || null,
        },
        { silent: true }
      )
      const processed = res.data?.processed ?? 0
      const failed = res.data?.failed ?? []
      if (failed.length > 0) {
        toast.error(`Bulk action partially applied: ${processed} succeeded, ${failed.length} failed`)
      } else {
        toast.success(`Bulk action applied to ${processed} candidate${processed === 1 ? "" : "s"}`)
      }
      setBulkAction("")
      setBulkReason("")
      setSelectedIds({})
      await fetchTasks()
    } catch (err: any) {
      toast.error(err.message || "Bulk action failed")
    } finally {
      setBulkBusy(false)
    }
  }

  async function updatePriority(taskId: string, priority: string) {
    const task = tasks.find((t) => t.id === taskId)
    const nextPriority = priority.toUpperCase()
    if (!task || (task.priority || "").toUpperCase() === nextPriority) return

    const originalTasks = [...tasks]
    setActing((a) => ({ ...a, [taskId]: true }))
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, priority: nextPriority } : t)))

    try {
      const res = await apiClient.post(
        "/review-queue/update-priority",
        { task_id: taskId, priority: nextPriority },
        { silent: true }
      )
      toast.success(`Priority updated to ${nextPriority} — SLA timer reset`)
      // Refresh so the backend-recalculated deadline renders immediately.
      await fetchTasks()
      return res
    } catch (err: any) {
      toast.error(err.message || "Failed to update priority")
      setTasks(originalTasks)
    } finally {
      setActing((a) => ({ ...a, [taskId]: false }))
    }
  }

  function openProbes(task: Task) {
    setProbesTask(task)
    setProbesDraft(
      (task.interview_probes || []).map((p) => ({
        category: p.category || "technical",
        question: p.question || "",
      }))
    )
  }

  function updateProbe(index: number, patch: Partial<Probe>) {
    setProbesDraft((draft) => draft.map((p, i) => (i === index ? { ...p, ...patch } : p)))
  }

  function addProbe() {
    setProbesDraft((draft) => [...draft, { category: "technical", question: "" }])
  }

  function removeProbe(index: number) {
    setProbesDraft((draft) => draft.filter((_, i) => i !== index))
  }

  async function saveProbes() {
    if (!probesTask) return
    const cleaned = probesDraft.filter((p) => p.question.trim())
    setSavingProbes(true)
    try {
      await apiClient.put(`/candidates/${probesTask.candidate_id}/probes`, {
        interview_probes: cleaned,
      })
      toast.success("Interview probes saved")
      setProbesTask(null)
      await fetchTasks()
    } catch (err: any) {
      toast.error(err.message || "Failed to save interview probes")
    } finally {
      setSavingProbes(false)
    }
  }

  async function generateProbesFor(task: Task) {
    setActing((a) => ({ ...a, [task.id]: true }))
    const toastId = toast.loading("Generating interview probes...")
    try {
      await apiClient.post(`/candidates/${task.candidate_id}/generate-probes`, {})
      toast.success("Interview probes generated", { id: toastId })
      await fetchTasks()
    } catch (err: any) {
      toast.error(err.message || "Failed to generate interview probes", { id: toastId })
    } finally {
      setActing((a) => ({ ...a, [task.id]: false }))
    }
  }

  const activeDeadline = (t: Task) => {
    const s = (t.status || "").toLowerCase()
    return s.includes("triage") ? t.triage_deadline_at : t.decision_deadline_at
  }

  if (loading && tasks.length === 0) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">Review Queue</h2>
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
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Human Review Queue</h2>
      </div>

      {/* Combined control bar: bulk actions (left) + filters (right) */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-3 bg-white rounded-xl border border-surface-border shadow-xs p-3">
        {!isAdmin() && (
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={bulkAction}
              onChange={(e) => setBulkAction(e.target.value)}
              disabled={bulkBusy}
              title="Choose a bulk action to apply to selected candidates"
              className="px-3 py-1.5 border border-surface-border rounded-lg text-sm bg-white font-medium"
            >
              <option value="">Bulk actions</option>
              {bulkOptionsForRole().map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <input
              value={bulkReason}
              onChange={(e) => setBulkReason(e.target.value)}
              placeholder="Reason (required to reject)…"
              className="px-3 py-1.5 border border-surface-border rounded-lg text-sm bg-white w-52"
            />
            <button
              onClick={applyBulk}
              disabled={bulkBusy || selectedCount === 0}
              className="px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-lg transition shadow-xs disabled:opacity-40"
            >
              Apply
            </button>
            <span className="text-xs text-surface-muted font-medium">{selectedCount} selected</span>
          </div>
        )}

        <div
          className={`flex flex-wrap items-center gap-2 ${
            isAdmin() ? "w-full lg:justify-end" : "lg:ml-auto"
          }`}
        >
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            title="Filter by SLA priority level"
            className="px-3 py-1.5 border border-surface-border rounded-lg text-sm bg-white"
          >
            <option value="">All Priorities</option>
            {slaPriorities.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            title="Filter by workflow status"
            className="px-3 py-1.5 border border-surface-border rounded-lg text-sm bg-white"
          >
            <option value="">All Statuses</option>
            {statusOptionsForRole().map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <select
            value={jobFilter}
            onChange={(e) => setJobFilter(e.target.value)}
            title="Filter by job"
            className="px-3 py-1.5 border border-surface-border rounded-lg text-sm bg-white max-w-[220px]"
          >
            <option value="">All Jobs</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title}
              </option>
            ))}
          </select>
          <button
            onClick={() => fetchTasks()}
            className="px-3 py-1.5 text-sm bg-brand-primary hover:bg-brand-primary/90 text-white font-medium rounded-lg flex items-center gap-1.5 transition shadow-xs"
          >
            <Filter className="w-3.5 h-3.5" /> Update
          </button>
          <button
            onClick={clearFilters}
            className="px-3 py-1.5 text-sm border border-surface-border bg-white hover:bg-surface-page text-surface-text font-medium rounded-lg flex items-center gap-1.5 transition shadow-xs"
          >
            <X className="w-3.5 h-3.5" /> Clear
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-surface-border shadow-xs overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase text-xs font-semibold">
            <tr>
              {!isAdmin() && (
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    title="Select all"
                    className="h-4 w-4 rounded border-surface-border text-brand-primary focus:ring-brand-primary"
                  />
                </th>
              )}
              <th className="px-4 py-3">Task / Ref</th>
              <th className="px-4 py-3">Candidate Applicant</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">SLA Deadline</th>
              <th className="px-4 py-3 min-w-[200px]">Reviewer Note / Comment</th>
              <th className="px-4 py-3 text-right min-w-[200px]">Available Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {tasks.map((t) => {
              const normStatus = (t.status || "").toLowerCase()
              const isEscalated = normStatus.includes("escalated")
              const slaResolved = t.sla_active === false || t.sla_phase === "resolved"
              const sla = slaCountdown(t.sla_deadline_at ?? activeDeadline(t))
              const isTriageStage = normStatus === "pending_triage" || normStatus === "escalated_triage"
              const isManagerStage = normStatus === "pending_manager_review" || normStatus === "escalated_manager"
              const isTerminal = normStatus === "approved" || normStatus === "rejected_at_triage" || normStatus === "rejected_by_manager" || normStatus === "edited_and_approved"
              const isBusy = acting[t.id]

              return (
                <tr
                  key={t.id}
                  className={`hover:bg-surface-page/40 transition ${isEscalated ? "bg-red-50/50" : ""}`}
                >
                  {/* Selection checkbox (hidden for admin) */}
                  {!isAdmin() && (
                    <td className="px-4 py-3.5 align-top">
                      <input
                        type="checkbox"
                        checked={!!selectedIds[t.id]}
                        onChange={() => toggleOne(t.id)}
                        title="Select this candidate"
                        className="h-4 w-4 rounded border-surface-border text-brand-primary focus:ring-brand-primary"
                      />
                    </td>
                  )}

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

                  {/* AI Match Score (same format as Jobs & Candidates table) */}
                  <td className="px-4 py-3.5 align-top">
                    {t.overall_score !== null && t.overall_score !== undefined ? (
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-sm text-surface-text">
                          {t.overall_score.toFixed(1)}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-surface-muted italic">Unscreened</span>
                    )}
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
                        title="Change priority — the SLA countdown resets for the current stage"
                        className="px-2 py-1 border border-surface-border rounded-md text-xs bg-white font-semibold shadow-xs"
                      >
                        {Array.from(
                          new Set([
                            ...(t.priority ? [t.priority.toUpperCase()] : []),
                            ...slaPriorities,
                          ])
                        ).map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className={priorityBadgeClass(t.priority)}>{t.priority}</span>
                    )}
                  </td>

                  {/* SLA Countdown Timer */}
                  <td className="px-4 py-3.5 align-top">
                    {slaResolved ? (
                      <span
                        title={
                          t.sla_resolved_at
                            ? `Resolved ${new Date(parseUtcMs(t.sla_resolved_at)).toLocaleString()}`
                            : "Workflow resolved"
                        }
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold ${
                          t.sla_outcome === "breached"
                            ? "bg-orange-100 text-orange-800 border border-orange-200"
                            : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                        }`}
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {t.sla_outcome === "breached" ? "Resolved (Breached)" : "Completed in SLA"}
                      </span>
                    ) : (
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
                    )}
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

                  {/* Actions Column — buttons stacked vertically */}
                  <td className="px-4 py-3.5 align-top">
                    <div className="flex flex-col items-end gap-1.5">
                      {/* Recruiter actions for Triage (Admin is read-only) */}
                      {isRecruiter() && isTriageStage && (
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

                      {/* Manager actions for Decision (Admin is read-only) */}
                      {isManager() && isManagerStage && (
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
                          {/*
                            Edit & Approve is temporarily hidden from the UI.
                            The click handler (act(t.id, "edit_and_approve")) and the
                            backend action remain intact for future re-enabling.
                          <button
                            id={`btn-edit-approve-${t.id.slice(0, 8)}`}
                            disabled={isBusy}
                            onClick={() => act(t.id, "edit_and_approve")}
                            title="Edit with comment and approve"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                          >
                            <Edit3 className="w-3.5 h-3.5" /> Edit & Approve
                          </button>
                          */}
                        </>
                      )}

                      {/* Interview Probes — shown for every role (Admin gets view-only) */}
                      <button
                        id={`btn-probes-${t.id.slice(0, 8)}`}
                        disabled={isBusy}
                        onClick={() => openProbes(t)}
                        title="View, edit, add or remove tailored interview probes"
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md shadow-xs transition disabled:opacity-50"
                      >
                        <ClipboardList className="w-3.5 h-3.5" /> Interview Probes
                      </button>

                      {isTerminal && (
                        <span className="text-xs text-surface-muted italic">Decision Logged</span>
                      )}
                    </div>
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

      {/* Interview Probes Modal */}
      {probesTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
              <div className="flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-brand-primary" />
                <h3 className="font-semibold text-surface-text">
                  Interview Probes — {probesTask.candidate_name || "Candidate"}
                </h3>
                {isAdmin() && (
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    View only
                  </span>
                )}
              </div>
              <button
                onClick={() => setProbesTask(null)}
                className="p-1 rounded-md hover:bg-surface-page text-surface-muted"
                title="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-3 overflow-y-auto">
              {probesDraft.length === 0 && (
                <div className="text-center py-6 space-y-2">
                  <p className="text-sm text-surface-muted italic">
                    {isAdmin() ? "No interview probes have been generated yet." : "No interview probes yet."}
                  </p>
                  {!isAdmin() && (
                    <button
                      onClick={async () => {
                        await generateProbesFor(probesTask)
                        setProbesTask(null)
                      }}
                      disabled={savingProbes}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded-md font-medium transition disabled:opacity-50"
                    >
                      <ClipboardList className="w-3.5 h-3.5" /> Generate Probes
                    </button>
                  )}
                </div>
              )}

              {probesDraft.map((probe, index) => (
                <div
                  key={index}
                  className="border border-surface-border rounded-lg p-3 space-y-2 bg-surface-page/40"
                >
                  <div className="flex items-center gap-2">
                    {isAdmin() ? (
                      <span className="px-2 py-1 border border-surface-border rounded-md text-xs bg-white font-semibold capitalize">
                        {probe.category || "technical"}
                      </span>
                    ) : (
                      <select
                        value={probe.category}
                        onChange={(e) => updateProbe(index, { category: e.target.value })}
                        className="px-2 py-1 border border-surface-border rounded-md text-xs bg-white font-semibold"
                      >
                        <option value="technical">Technical</option>
                        <option value="behavioral">Behavioral</option>
                        <option value="gap">Gap / Red-flag</option>
                      </select>
                    )}
                    {!isAdmin() && (
                      <button
                        onClick={() => removeProbe(index)}
                        title="Delete this question"
                        className="ml-auto inline-flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" /> Delete
                      </button>
                    )}
                  </div>
                  {isAdmin() ? (
                    <p className="text-sm text-surface-text whitespace-pre-wrap">
                      {probe.question || "—"}
                    </p>
                  ) : (
                    <textarea
                      value={probe.question}
                      onChange={(e) => updateProbe(index, { question: e.target.value })}
                      rows={2}
                      placeholder="Interview question..."
                      className="w-full px-2.5 py-1.5 border border-surface-border rounded-lg text-sm bg-white focus:ring-1 focus:ring-brand-primary"
                    />
                  )}
                </div>
              ))}

              {!isAdmin() && (
                <button
                  onClick={addProbe}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-brand-primary border border-brand-primary/30 bg-indigo-50 hover:bg-indigo-100 rounded-md transition"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Question
                </button>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-surface-border">
              {isAdmin() && (
                <span className="mr-auto text-xs text-surface-muted italic">
                  View-only — probes cannot be modified by admins.
                </span>
              )}
              <button
                onClick={() => setProbesTask(null)}
                className="px-3 py-1.5 text-sm border border-surface-border rounded-lg hover:bg-surface-page transition"
              >
                {isAdmin() ? "Close" : "Cancel"}
              </button>
              {!isAdmin() && (
                <button
                  onClick={saveProbes}
                  disabled={savingProbes}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-sm bg-brand-primary hover:bg-brand-primary/90 text-white rounded-lg font-medium transition disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" /> {savingProbes ? "Saving…" : "Save"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

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
