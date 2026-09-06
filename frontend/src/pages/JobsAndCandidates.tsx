import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { isAdmin, isRecruiter } from "../lib/auth"
import { Skeleton } from "../components/Skeleton"

interface Job {
  id: string
  title: string
  department: string
  priority: string
}

interface Candidate {
  id: string
  full_name: string
  email: string
  status: string
  overall_score: number | null
  priority: string
  years_of_experience: number
  skills: string[]
}

export function JobsAndCandidates() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [selectedJob, setSelectedJob] = useState<string>("")
  const [newJobTitle, setNewJobTitle] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchJobs()
    fetchCandidates()
  }, [selectedJob])

  async function fetchJobs() {
    try {
      const res = await apiClient.get("/jobs")
      setJobs(res.data)
    } catch (err: any) {
      toast.error(err.message || "Failed to load jobs")
    }
  }

  async function fetchCandidates() {
    try {
      const params = selectedJob ? { job_id: selectedJob } : {}
      const res = await apiClient.get("/candidates", { params })
      setCandidates(res.data)
    } catch (err: any) {
      toast.error(err.message || "Failed to load candidates")
    } finally {
      setLoading(false)
    }
  }

  async function createJob(e: React.FormEvent) {
    e.preventDefault()
    if (!newJobTitle.trim()) return
    setSubmitting(true)
    try {
      await apiClient.post("/jobs", { title: newJobTitle })
      setNewJobTitle("")
      toast.success("Job created")
      await fetchJobs()
    } catch (err: any) {
      toast.error(err.message || "Failed to create job")
    } finally {
      setSubmitting(false)
    }
  }

  async function uploadCandidate(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setSubmitting(true)
    const form = new FormData()
    form.append("file", file)
    if (selectedJob) form.append("job_id", selectedJob)
    try {
      await apiClient.post("/candidates", form, { headers: { "Content-Type": "multipart/form-data" } })
      setFile(null)
      toast.success("Candidate uploaded")
      await fetchCandidates()
    } catch (err: any) {
      toast.error(err.message || "Failed to upload candidate")
    } finally {
      setSubmitting(false)
    }
  }

  async function runPipeline(candidateId: string) {
    try {
      await apiClient.post("/pipeline/run", { candidate_id: candidateId })
      toast.success("Pipeline started")
      await fetchCandidates()
    } catch (err: any) {
      toast.error(err.message || "Failed to run pipeline")
    }
  }

  if (loading) {
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
      <h2 className="text-2xl font-heading font-semibold text-surface-text">Jobs & Candidates</h2>

      {(isAdmin() || isRecruiter()) && (
        <form onSubmit={createJob} className="bg-white p-4 rounded-lg border border-surface-border flex gap-2">
          <input
            placeholder="New job title"
            value={newJobTitle}
            onChange={(e) => setNewJobTitle(e.target.value)}
            className="flex-1 px-3 py-2 border border-surface-border rounded-md"
          />
          <button type="submit" disabled={submitting} className="px-4 py-2 bg-brand-primary text-white rounded-md disabled:opacity-50">Create Job</button>
        </form>
      )}

      <div className="bg-white p-4 rounded-lg border border-surface-border">
        <label className="block text-sm font-medium mb-2">Filter by job</label>
        <select
          value={selectedJob}
          onChange={(e) => setSelectedJob(e.target.value)}
          className="w-full px-3 py-2 border border-surface-border rounded-md"
        >
          <option value="">All jobs</option>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>{j.title}</option>
          ))}
        </select>
      </div>

      {(isAdmin() || isRecruiter()) && (
        <form onSubmit={uploadCandidate} className="bg-white p-4 rounded-lg border border-surface-border space-y-3">
          <h3 className="font-medium">Upload CV</h3>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm"
          />
          <button type="submit" disabled={submitting || !file} className="px-4 py-2 bg-brand-primary text-white rounded-md disabled:opacity-50">Upload</button>
        </form>
      )}

      <div className="bg-white rounded-lg border border-surface-border overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.id} className="border-t border-surface-border">
                <td className="px-4 py-3">{c.full_name}</td>
                <td className="px-4 py-3">{c.status}</td>
                <td className="px-4 py-3">{c.overall_score?.toFixed(1) ?? "-"}</td>
                <td className="px-4 py-3">{c.priority}</td>
                <td className="px-4 py-3">
                  {(isAdmin() || isRecruiter()) && (
                    <button
                      onClick={() => runPipeline(c.id)}
                      className="px-3 py-1 text-xs bg-brand-accent text-white rounded-md"
                    >
                      Run pipeline
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {candidates.length === 0 && (
          <div className="p-6 text-center text-surface-muted text-sm">No candidates found.</div>
        )}
      </div>
    </div>
  )
}
