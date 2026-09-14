import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { AlertTriangle, Briefcase, Building2, ClipboardList, MapPin, Pencil, Save, Trash2, X } from "lucide-react"

export interface JobDetails {
  id: string
  title: string
  department: string
  description: string
  location: string
  priority: string
  skills: string[]
}

interface JobDetailsModalProps {
  job: JobDetails | null
  isOpen: boolean
  /** Admins and recruiters may edit/delete; other roles get a read-only view. */
  canManage: boolean
  /** Active SLA priorities, offered as options for the job's default priority. */
  priorityOptions: string[]
  onClose: () => void
  onSaved: (job: JobDetails) => void
  onDeleted: (jobId: string) => void
}

interface JobForm {
  title: string
  department: string
  location: string
  priority: string
  description: string
  skillsText: string
}

function formFromJob(job: JobDetails): JobForm {
  return {
    title: job.title || "",
    department: job.department || "",
    location: job.location || "",
    priority: (job.priority || "MEDIUM").toUpperCase(),
    description: job.description || "",
    skillsText: (job.skills || []).join(", "),
  }
}

function priorityBadgeClass(priority: string): string {
  switch ((priority || "MEDIUM").toUpperCase()) {
    case "HIGH":
      return "bg-red-100 text-red-800 border-red-200"
    case "LOW":
      return "bg-green-100 text-green-800 border-green-200"
    default:
      return "bg-yellow-100 text-yellow-800 border-yellow-200"
  }
}

export function JobDetailsModal({ job, isOpen, canManage, priorityOptions, onClose, onSaved, onDeleted }: JobDetailsModalProps) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [form, setForm] = useState<JobForm>({ title: "", department: "", location: "", priority: "MEDIUM", description: "", skillsText: "" })

  // Reset the modal state (and pre-fill the edit form) whenever it opens for a
  // different job, so a previous edit/confirmation never leaks across jobs.
  useEffect(() => {
    if (isOpen && job) {
      setForm(formFromJob(job))
      setEditing(false)
      setConfirmDelete(false)
    }
  }, [isOpen, job])

  if (!isOpen || !job) return null

  // Capture the narrowed values so the async handlers below keep the non-null
  // type (TypeScript drops prop narrowing inside closures).
  const jobId = job.id
  const jobTitle = job.title

  const set = (patch: Partial<JobForm>) => setForm((prev) => ({ ...prev, ...patch }))

  async function saveChanges() {
    if (!form.title.trim()) {
      toast.error("Job title is required")
      return
    }
    setSaving(true)
    try {
      const skills = form.skillsText.split(",").map((s) => s.trim()).filter((s) => s.length > 0)
      const res = await apiClient.patch(`/jobs/${jobId}`, {
        title: form.title.trim(),
        department: form.department.trim(),
        location: form.location.trim(),
        priority: form.priority,
        description: form.description.trim(),
        skills,
      })
      toast.success("Job details updated")
      onSaved(res.data as JobDetails)
      setEditing(false)
    } catch (err: any) {
      toast.error(err.message || "Failed to update job")
    } finally {
      setSaving(false)
    }
  }

  async function deleteJob() {
    setDeleting(true)
    try {
      await apiClient.delete(`/jobs/${jobId}`)
      toast.success(`Job "${jobTitle}" deleted`)
      onDeleted(jobId)
      setConfirmDelete(false)
    } catch (err: any) {
      toast.error(err.message || "Failed to delete job")
    } finally {
      setDeleting(false)
    }
  }

  const priorityChoices = Array.from(new Set([...priorityOptions, form.priority])).filter(Boolean)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 md:p-6 animate-in fade-in duration-200">
      <div
        className="bg-white rounded-2xl shadow-2xl border border-surface-border w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between bg-surface-page/60 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary shrink-0">
              <Briefcase className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="font-heading font-bold text-lg text-surface-text truncate">{job.title || "Job Details"}</h3>
              <div className="flex items-center gap-2 text-xs text-surface-muted mt-0.5">
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${priorityBadgeClass(form.priority || job.priority)}`}>
                  {form.priority || job.priority}
                </span>
                <span className="font-mono">ID: {job.id.slice(0, 8)}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            title="Close"
            className="p-1.5 rounded-lg text-surface-muted hover:text-surface-text hover:bg-surface-page transition shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {editing ? (
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-surface-muted mb-1 font-medium">Job Title *</label>
                <input
                  value={form.title}
                  onChange={(e) => set({ title: e.target.value })}
                  className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-primary/20"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-surface-muted mb-1 font-medium">Department</label>
                  <input
                    value={form.department}
                    onChange={(e) => set({ department: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-surface-muted mb-1 font-medium">Location</label>
                  <input
                    value={form.location}
                    onChange={(e) => set({ location: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-surface-muted mb-1 font-medium">Default Priority</label>
                  <select
                    value={form.priority}
                    onChange={(e) => set({ priority: e.target.value })}
                    className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white"
                  >
                    {priorityChoices.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs text-surface-muted mb-1 font-medium">Required Skills / Rubric Criteria (comma-separated)</label>
                <input
                  value={form.skillsText}
                  onChange={(e) => set({ skillsText: e.target.value })}
                  placeholder="Python, Docker, SQL"
                  className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white"
                />
                <p className="text-[11px] text-surface-muted mt-1">The auto-provisioned scoring rubric is derived from these skills.</p>
              </div>
              <div>
                <label className="block text-xs text-surface-muted mb-1 font-medium">Role Description & Requirements</label>
                <textarea
                  value={form.description}
                  onChange={(e) => set({ description: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <DetailRow icon={<Building2 className="w-4 h-4" />} label="Department" value={job.department || "—"} />
              <DetailRow icon={<MapPin className="w-4 h-4" />} label="Location" value={job.location || "—"} />
              <DetailRow
                icon={<ClipboardList className="w-4 h-4" />}
                label="Required Skills"
                value={job.skills && job.skills.length > 0 ? job.skills.join(", ") : "No skills specified"}
              />
              <div>
                <div className="text-xs font-semibold uppercase text-surface-muted mb-1">Role Description & Requirements</div>
                <p className="text-sm text-surface-text whitespace-pre-wrap bg-surface-page/50 border border-surface-border rounded-lg p-3">
                  {job.description || "No description provided."}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-surface-border flex flex-wrap items-center justify-between gap-2 bg-white shrink-0">
          {canManage && !editing ? (
            <button
              onClick={() => setConfirmDelete(true)}
              title="Delete this job vacancy"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 font-medium rounded-lg transition"
            >
              <Trash2 className="w-4 h-4" /> Delete Job
            </button>
          ) : (
            <span />
          )}

          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <button
                  onClick={() => {
                    setForm(formFromJob(job))
                    setEditing(false)
                  }}
                  disabled={saving}
                  className="px-3.5 py-2 text-sm border border-surface-border rounded-lg hover:bg-surface-page transition disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={saveChanges}
                  disabled={saving}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm bg-brand-primary hover:bg-brand-primary/90 text-white rounded-lg font-medium transition disabled:opacity-50"
                >
                  <Save className="w-4 h-4" /> {saving ? "Saving…" : "Save Changes"}
                </button>
              </>
            ) : (
              <>
                <button onClick={onClose} className="px-3.5 py-2 text-sm border border-surface-border rounded-lg hover:bg-surface-page transition">
                  Close
                </button>
                {canManage && (
                  <button
                    onClick={() => setEditing(true)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm bg-brand-primary hover:bg-brand-primary/90 text-white rounded-lg font-medium transition"
                  >
                    <Pencil className="w-4 h-4" /> Edit Details
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Delete confirmation dialog (overlays the card) */}
        {confirmDelete && (
          <div className="absolute inset-0 z-10 bg-white/95 backdrop-blur-xs flex items-center justify-center p-6">
            <div className="max-w-md w-full bg-white border border-red-200 rounded-xl shadow-xl p-5 space-y-4 text-center">
              <div className="w-11 h-11 mx-auto rounded-full bg-red-100 flex items-center justify-center text-red-600">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h4 className="font-semibold text-surface-text">Delete this job?</h4>
                <p className="text-sm text-surface-muted">
                  <strong>{job.title}</strong> will be permanently deleted. Its review tasks, SLA rules and rubric are removed too; unlinked candidates stay in the talent pool.
                </p>
              </div>
              <div className="flex items-center justify-center gap-2 pt-1">
                <button
                  onClick={() => setConfirmDelete(false)}
                  disabled={deleting}
                  className="px-3.5 py-2 text-sm border border-surface-border rounded-lg hover:bg-surface-page transition disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={deleteJob}
                  disabled={deleting}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition disabled:opacity-50"
                >
                  <Trash2 className="w-4 h-4" /> {deleting ? "Deleting…" : "Yes, Delete Job"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DetailRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5 text-brand-primary shrink-0">{icon}</span>
      <div>
        <div className="text-xs font-semibold uppercase text-surface-muted">{label}</div>
        <div className="text-sm text-surface-text">{value}</div>
      </div>
    </div>
  )
}