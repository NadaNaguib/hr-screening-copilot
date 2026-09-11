import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { isAdmin, isRecruiter } from "../lib/auth"
import { Skeleton } from "../components/Skeleton"
import {
  Briefcase,
  Trash2,
  Sparkles,
  UploadCloud,
  Play,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  UserCheck,
} from "lucide-react"
import { CvViewerModal } from "../components/CvViewerModal"

// Formats advertised as supported in the UI. The extension is authoritative
// (browsers sometimes report generic/empty MIME types for Office documents).
const SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]
const SUPPORTED_MIME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "application/vnd.ms-word",
  "text/plain",
]
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

function isSupportedFile(f: File): boolean {
  const name = f.name.toLowerCase()
  if (SUPPORTED_EXTENSIONS.some((ext) => name.endsWith(ext))) return true
  const type = (f.type || "").toLowerCase()
  if (type.startsWith("text/")) return true
  return SUPPORTED_MIME_TYPES.includes(type)
}

function validateCvFile(f: File): string | null {
  if (!isSupportedFile(f)) {
    return `Unsupported file format "${f.name}". Please upload a PDF, DOCX, or TXT file.`
  }
  if (f.size > MAX_FILE_SIZE_BYTES) {
    return `File is too large (${(f.size / 1024 / 1024).toFixed(1)}MB). Maximum size is 10MB.`
  }
  return null
}

interface Job {
  id: string
  title: string
  department: string
  description: string
  location: string
  priority: string
  skills: string[]
}

interface Candidate {
  id: string
  full_name: string
  email: string
  status: string
  overall_score: number | null
  years_of_experience: number
  skills: string[]
}

export function JobsAndCandidates() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [selectedJob, setSelectedJob] = useState<string>("")
  const [newJobTitle, setNewJobTitle] = useState("")
  const [newJobDept, setNewJobDept] = useState("Engineering")
  const [newJobDescription, setNewJobDescription] = useState("")
  const [newJobSkills, setNewJobSkills] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [mimicking, setMimicking] = useState(false)
  const [deletingJob, setDeletingJob] = useState(false)
  const [deletingCandidateId, setDeletingCandidateId] = useState<string | null>(null)
  const [runningPipelineId, setRunningPipelineId] = useState<string | null>(null)
  const [expandedSkills, setExpandedSkills] = useState<Record<string, boolean>>({})
  const [selectedCv, setSelectedCv] = useState<{ id: string; name?: string } | null>(null)

  useEffect(() => {
    fetchJobs()
  }, [])

  useEffect(() => {
    if (selectedJob) {
      fetchCandidates()
    } else {
      setCandidates([])
      setLoading(false)
    }
  }, [selectedJob])

  async function fetchJobs() {
    try {
      const res = await apiClient.get("/jobs")
      setJobs(res.data)
      if (res.data.length > 0 && !selectedJob) {
        setSelectedJob(res.data[0].id)
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to load jobs")
    } finally {
      setLoading(false)
    }
  }

  async function fetchCandidates() {
    if (!selectedJob) return
    try {
      const res = await apiClient.get("/candidates", { params: { job_id: selectedJob } })
      setCandidates(res.data)
    } catch (err: any) {
      toast.error(err.message || "Failed to load candidates")
    }
  }

  async function createJob(e: React.FormEvent) {
    e.preventDefault()
    if (!newJobTitle.trim()) return
    setSubmitting(true)
    try {
      const skills = newJobSkills
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
      const res = await apiClient.post("/jobs", {
        title: newJobTitle.trim(),
        department: newJobDept.trim(),
        description: newJobDescription.trim(),
        skills,
      })
      const createdId = res.data.id
      toast.success(`Job "${newJobTitle}" created & selected!`)
      setNewJobTitle("")
      setNewJobDescription("")
      setNewJobSkills("")
      await fetchJobs()
      setSelectedJob(createdId)
    } catch (err: any) {
      toast.error(err.message || "Failed to create job")
    } finally {
      setSubmitting(false)
    }
  }

  async function deleteJob() {
    if (!selectedJob) return
    const curJob = jobs.find((j) => j.id === selectedJob)
    if (!confirm(`Are you sure you want to delete "${curJob?.title || 'this job'}"? Any unlinked candidates will remain in the pool.`)) {
      return
    }
    setDeletingJob(true)
    try {
      await apiClient.delete(`/jobs/${selectedJob}`)
      toast.success("Job deleted successfully")
      const updatedJobs = jobs.filter((j) => j.id !== selectedJob)
      setJobs(updatedJobs)
      setSelectedJob(updatedJobs.length > 0 ? updatedJobs[0].id : "")
    } catch (err: any) {
      toast.error(err.message || "Failed to delete job")
    } finally {
      setDeletingJob(false)
    }
  }

  async function mimicCandidate() {
    if (!selectedJob) {
      toast.error("Please select a job first")
      return
    }
    setMimicking(true)
    const curJob = jobs.find((j) => j.id === selectedJob)
    const toastId = toast.loading(`Generating tailored CV for ${curJob?.title || "selected job"}...`)
    try {
      const res = await apiClient.post(`/jobs/${selectedJob}/mimic-candidate`, {})
      toast.success(`Candidate ${res.data.full_name} synthesized & screened!`, { id: toastId })
      await fetchCandidates()
    } catch (err: any) {
      toast.error(err.message || "Failed to generate candidate", { id: toastId })
    } finally {
      setMimicking(false)
    }
  }

  async function deleteCandidate(candidateId: string, name: string) {
    if (!confirm(`Delete candidate "${name}" and all associated review scores?`)) return
    setDeletingCandidateId(candidateId)
    try {
      await apiClient.delete(`/candidates/${candidateId}`)
      toast.success("Candidate deleted")
      await fetchCandidates()
    } catch (err: any) {
      toast.error(err.message || "Failed to delete candidate")
    } finally {
      setDeletingCandidateId(null)
    }
  }

  async function uploadCandidate(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !selectedJob) {
      toast.error("Select a job before uploading a candidate")
      return
    }
    const fileError = validateCvFile(file)
    if (fileError) {
      toast.error(fileError)
      return
    }
    setSubmitting(true)
    const form = new FormData()
    // The backend reads the file from the multipart field named "file" and the
    // job id from either the form field or the query string.
    form.append("file", file)
    form.append("job_id", selectedJob)
    try {
      // No manual Content-Type: the browser adds `multipart/form-data; boundary=...`.
      await apiClient.post("/candidates", form, { params: { job_id: selectedJob } })
      setFile(null)
      toast.success("Candidate CV uploaded successfully")
      await fetchCandidates()
    } catch (err: any) {
      toast.error(err.message || "Failed to upload candidate")
    } finally {
      setSubmitting(false)
    }
  }

  async function runPipeline(candidateId: string) {
    setRunningPipelineId(candidateId)
    const toastId = toast.loading("Executing multi-agent screening pipeline...")
    try {
      const res = await apiClient.post("/pipeline/run", { candidate_id: candidateId })
      toast.success(`Pipeline completed! Score: ${(res.data.overall_score || 0).toFixed(1)}%`, { id: toastId })
      await fetchCandidates()
    } catch (err: any) {
      toast.error(err.message || "Failed to run pipeline", { id: toastId })
    } finally {
      setRunningPipelineId(null)
    }
  }

  const activeJob = jobs.find((j) => j.id === selectedJob)

  if (loading && jobs.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">Jobs & Candidates</h2>
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-heading font-bold text-surface-text tracking-tight">Jobs & Talent Pool</h2>
          <p className="text-sm text-surface-muted">Manage screening roles, upload resumes, synthesize sample profiles, and execute agent pipelines.</p>
        </div>
      </div>

      {/* Role Selection Bar */}
      <div className="bg-white p-4 rounded-xl border border-surface-border shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1">
          <label className="block text-xs font-semibold uppercase text-surface-muted mb-1.5 flex items-center gap-1.5">
            <Briefcase className="w-3.5 h-3.5 text-brand-primary" /> Active Job Position
          </label>
          <select
            value={selectedJob}
            onChange={(e) => setSelectedJob(e.target.value)}
            className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white font-medium focus:ring-2 focus:ring-brand-primary/20"
          >
            <option value="" disabled>Choose a job...</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title} {j.department ? `(${j.department})` : ""}
              </option>
            ))}
          </select>
        </div>

        {activeJob && (
          <div className="flex items-center gap-2 pt-2 md:pt-5">
            <button
              onClick={mimicCandidate}
              disabled={mimicking}
              title="Generate a sample candidate CV matching this role and automatically run agentic screening"
              className="px-3.5 py-2 text-sm bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg shadow-xs flex items-center gap-2 transition disabled:opacity-50"
            >
              <Sparkles className={`w-4 h-4 ${mimicking ? "animate-spin" : ""}`} />
              {mimicking ? "Synthesizing CV…" : "Mimic CV & Match"}
            </button>

            {(isAdmin() || isRecruiter()) && (
              <button
                onClick={deleteJob}
                disabled={deletingJob}
                title="Delete this job vacancy"
                className="px-3 py-2 text-sm bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 font-medium rounded-lg transition disabled:opacity-50 flex items-center gap-1.5"
              >
                <Trash2 className="w-4 h-4" />
                Delete Job
              </button>
            )}
          </div>
        )}
      </div>

      {/* Active Job Specs Summary Card */}
      {activeJob && (
        <div className="bg-gradient-to-r from-blue-50/70 to-indigo-50/70 p-4 rounded-xl border border-blue-100 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-surface-text text-base">{activeJob.title}</span>
              {activeJob.department && (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {activeJob.department}
                </span>
              )}
            </div>
            {activeJob.description && (
              <p className="text-xs text-surface-muted max-w-2xl line-clamp-2">{activeJob.description}</p>
            )}
            {activeJob.skills && activeJob.skills.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {activeJob.skills.map((skill, i) => (
                  <span key={i} className="px-2 py-0.5 bg-white border border-blue-200 text-blue-900 rounded text-xs font-mono">
                    {skill}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="text-xs text-surface-muted whitespace-nowrap">
            <span className="font-semibold text-surface-text">{candidates.length}</span> candidates in pipeline
          </div>
        </div>
      )}

      {/* Creation and Upload Row */}
      {(isAdmin() || isRecruiter()) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Create Job Form */}
          <form onSubmit={createJob} className="bg-white p-5 rounded-xl border border-surface-border shadow-xs space-y-3">
            <h3 className="font-semibold text-surface-text text-base flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-brand-primary" /> Create New Vacancy
            </h3>
            <div>
              <label className="block text-xs text-surface-muted mb-1 font-medium">Job Title *</label>
              <input
                placeholder="e.g. Senior Backend Engineer"
                value={newJobTitle}
                onChange={(e) => setNewJobTitle(e.target.value)}
                className="w-full px-3 py-1.5 border border-surface-border rounded-lg text-sm"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-surface-muted mb-1 font-medium">Department</label>
                <input
                  placeholder="e.g. Engineering"
                  value={newJobDept}
                  onChange={(e) => setNewJobDept(e.target.value)}
                  className="w-full px-3 py-1.5 border border-surface-border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-surface-muted mb-1 font-medium">Key Skills (comma-separated)</label>
                <input
                  placeholder="Python, Docker, SQL"
                  value={newJobSkills}
                  onChange={(e) => setNewJobSkills(e.target.value)}
                  className="w-full px-3 py-1.5 border border-surface-border rounded-lg text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-surface-muted mb-1 font-medium">Role Description & Requirements</label>
              <textarea
                placeholder="Key responsibilities and qualifications required..."
                value={newJobDescription}
                onChange={(e) => setNewJobDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-1.5 border border-surface-border rounded-lg text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={submitting || !newJobTitle.trim()}
              className="w-full py-2 bg-brand-primary text-white rounded-lg text-sm font-medium hover:bg-brand-primary/90 transition disabled:opacity-50"
            >
              {submitting ? "Creating Job…" : "Create Vacancy"}
            </button>
          </form>

          {/* Upload CV Form */}
          <form onSubmit={uploadCandidate} className="bg-white p-5 rounded-xl border border-surface-border shadow-xs space-y-3 flex flex-col justify-between">
            <div className="space-y-3">
              <h3 className="font-semibold text-surface-text text-base flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-brand-primary" /> Upload Candidate Resume
              </h3>
              <p className="text-xs text-surface-muted">
                Accepts PDF, DOCX, or TXT format. Candidate will be assigned to <strong>{activeJob ? activeJob.title : "the selected job"}</strong>.
              </p>
              <div className="border-2 border-dashed border-surface-border hover:border-brand-primary/50 rounded-xl p-4 text-center transition">
                <input
                  type="file"
                  id="cv-file-input"
                  accept=".pdf,.docx,.doc,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/msword,text/plain"
                  onChange={(e) => {
                    const picked = e.target.files?.[0] || null
                    if (picked) {
                      const fileError = validateCvFile(picked)
                      if (fileError) {
                        toast.error(fileError)
                        e.target.value = ""
                        setFile(null)
                        return
                      }
                    }
                    setFile(picked)
                  }}
                  className="hidden"
                />
                <label htmlFor="cv-file-input" className="cursor-pointer block">
                  <FileText className="w-8 h-8 text-brand-primary/60 mx-auto mb-1" />
                  <span className="text-sm font-medium text-surface-text block">
                    {file ? file.name : "Click to browse or drop resume file"}
                  </span>
                  <span className="text-xs text-surface-muted">Max file size 10MB</span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || !file || !selectedJob}
              className="w-full py-2 bg-brand-primary text-white rounded-lg text-sm font-medium hover:bg-brand-primary/90 transition disabled:opacity-50"
            >
              {submitting ? "Parsing & Uploading…" : "Upload & Parse Resume"}
            </button>
          </form>
        </div>
      )}

      {/* Candidate Pipeline Table */}
      <div className="bg-white rounded-xl border border-surface-border shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-surface-text">Applicant Candidates Pool</h3>
            <p className="text-xs text-surface-muted">Filtered for: <span className="font-semibold text-surface-text">{activeJob?.title || "No job selected"}</span></p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
            {candidates.length} Applicants
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface-page text-surface-muted uppercase text-xs font-semibold">
              <tr>
                <th className="px-4 py-3">Applicant Name</th>
                <th className="px-4 py-3">Experience</th>
                <th className="px-4 py-3">Parsed Skills</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {candidates.map((c) => {
                const isRunning = runningPipelineId === c.id
                const isDeleting = deletingCandidateId === c.id
                return (
                  <tr key={c.id} className="hover:bg-surface-page/50 transition">
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-surface-text">{c.full_name || "Applicant"}</div>
                      <div className="text-xs text-surface-muted font-mono">{c.email || c.id.slice(0, 8)}</div>
                    </td>
                    <td className="px-4 py-3.5 text-surface-muted text-xs">
                      {c.years_of_experience ? `${c.years_of_experience.toFixed(1)} yrs` : "—"}
                    </td>
                    <td className="px-4 py-3.5">
                      {(() => {
                        const skills = c.skills || []
                        const isExpanded = expandedSkills[c.id]
                        if (skills.length === 0) {
                          return <span className="text-xs text-surface-muted italic">None parsed</span>
                        }
                        const displayedSkills = isExpanded ? skills : skills.slice(0, 4)
                        const remaining = skills.slice(4)

                        return (
                          <div className="space-y-1.5 max-w-sm">
                            <div className="flex flex-wrap gap-1">
                              {displayedSkills.map((sk, i) => (
                                <span key={i} className="px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-700 font-mono">
                                  {sk}
                                </span>
                              ))}
                              {remaining.length > 0 && !isExpanded && (
                                <button
                                  type="button"
                                  onClick={() => setExpandedSkills((prev) => ({ ...prev, [c.id]: true }))}
                                  title={`Remaining skills: ${remaining.join(", ")} (Click to expand)`}
                                  className="px-1.5 py-0.5 rounded text-xs bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary font-semibold font-mono transition cursor-pointer border border-brand-primary/20"
                                >
                                  +{remaining.length} more
                                </button>
                              )}
                            </div>
                            {isExpanded && remaining.length > 0 && (
                              <button
                                type="button"
                                onClick={() => setExpandedSkills((prev) => ({ ...prev, [c.id]: false }))}
                                className="text-[11px] text-brand-primary hover:underline font-medium block cursor-pointer"
                              >
                                Show less
                              </button>
                            )}
                          </div>
                        )
                      })()}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        c.status === "screened"
                          ? "bg-green-100 text-green-800"
                          : c.status === "processing"
                          ? "bg-yellow-100 text-yellow-800 animate-pulse"
                          : "bg-blue-100 text-blue-800"
                      }`}>
                        {c.status === "screened" && <CheckCircle2 className="w-3 h-3" />}
                        {c.status === "processing" && <Clock className="w-3 h-3" />}
                        {c.status === "uploaded" && <UserCheck className="w-3 h-3" />}
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      {c.overall_score !== null && c.overall_score !== undefined ? (
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono font-bold text-sm text-surface-text">
                            {c.overall_score.toFixed(1)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-surface-muted italic">Unscreened</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right space-x-2 whitespace-nowrap">
                      <button
                        onClick={() => setSelectedCv({ id: c.id, name: c.full_name })}
                        title="View full original CV"
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-indigo-50 hover:bg-indigo-100 text-brand-primary border border-brand-primary/30 rounded-md font-medium transition"
                      >
                        <FileText className="w-3 h-3" />
                        View CV
                      </button>
                      {(isAdmin() || isRecruiter()) && (
                        <>
                          <button
                            onClick={() => runPipeline(c.id)}
                            disabled={isRunning || isDeleting}
                            title="Execute multi-agent screening on this candidate"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-brand-primary hover:bg-brand-primary/90 text-white rounded-md font-medium transition disabled:opacity-50"
                          >
                            <Play className={`w-3 h-3 ${isRunning ? "animate-spin" : ""}`} />
                            {isRunning ? "Screening…" : "Run pipeline"}
                          </button>
                          <button
                            onClick={() => deleteCandidate(c.id, c.full_name)}
                            disabled={isDeleting || isRunning}
                            title="Remove candidate from pool"
                            className="inline-flex items-center p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition disabled:opacity-50"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {candidates.length === 0 && (
            <div className="p-8 text-center space-y-2">
              <AlertCircle className="w-8 h-8 text-surface-muted mx-auto" />
              <p className="text-sm font-medium text-surface-text">No candidates found for this job</p>
              <p className="text-xs text-surface-muted">Upload a candidate resume or click <strong>Mimic CV & Match</strong> above to generate a sample profile instantly.</p>
            </div>
          )}
        </div>
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
