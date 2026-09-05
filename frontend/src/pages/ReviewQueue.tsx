import { useEffect, useState } from "react"
import { apiClient } from "../lib/apiClient"
import { isAdmin, isManager, isRecruiter } from "../lib/auth"

interface Task {
  id: string
  candidate_id: string
  job_id: string | null
  status: string
  triage_reason: string | null
  manager_comment: string | null
  admin_override_reason: string | null
}

export function ReviewQueue() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [reason, setReason] = useState<Record<string, string>>({})

  useEffect(() => {
    fetchTasks()
  }, [])

  async function fetchTasks() {
    const res = await apiClient.get("/review-queue")
    setTasks(res.data)
  }

  async function act(taskId: string, action: string) {
    const endpoint = action.startsWith("forward") || action === "reject_at_triage" ? "/review-queue/triage" : "/review-queue/decide"
    await apiClient.post(endpoint, { task_id: taskId, action, reason: reason[taskId] || "" })
    fetchTasks()
  }

  async function override(taskId: string) {
    await apiClient.post("/review-queue/admin-override", { task_id: taskId, reason: reason[taskId] || "" })
    fetchTasks()
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
              <th className="px-4 py-3">Reason / Comment</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id} className="border-t border-surface-border">
                <td className="px-4 py-3 font-mono text-xs">{t.id.slice(0, 8)}</td>
                <td className="px-4 py-3">{t.candidate_id.slice(0, 8)}</td>
                <td className="px-4 py-3">{t.status}</td>
                <td className="px-4 py-3">
                  <input
                    value={reason[t.id] || ""}
                    onChange={(e) => setReason((r) => ({ ...r, [t.id]: e.target.value }))}
                    placeholder="Reason..."
                    className="w-full px-2 py-1 border border-surface-border rounded-md text-xs"
                  />
                </td>
                <td className="px-4 py-3 space-x-1">
                  {isRecruiter() && t.status === "pending_triage" && (
                    <>
                      <button onClick={() => act(t.id, "forward_to_manager")} className="px-2 py-1 text-xs bg-brand-primary text-white rounded-md">Forward</button>
                      <button onClick={() => act(t.id, "reject_at_triage")} className="px-2 py-1 text-xs bg-semantic-danger text-white rounded-md">Reject</button>
                    </>
                  )}
                  {isManager() && t.status === "pending_manager_review" && (
                    <>
                      <button onClick={() => act(t.id, "approve")} className="px-2 py-1 text-xs bg-semantic-success text-white rounded-md">Approve</button>
                      <button onClick={() => act(t.id, "reject")} className="px-2 py-1 text-xs bg-semantic-danger text-white rounded-md">Reject</button>
                      <button onClick={() => act(t.id, "edit_and_approve")} className="px-2 py-1 text-xs bg-brand-accent text-white rounded-md">Edit & Approve</button>
                    </>
                  )}
                  {isAdmin() && ["pending_triage", "pending_manager_review"].includes(t.status) && (
                    <button onClick={() => override(t.id)} className="px-2 py-1 text-xs bg-semantic-warning text-white rounded-md">Override</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
