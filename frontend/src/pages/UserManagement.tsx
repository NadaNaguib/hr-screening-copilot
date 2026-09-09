import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
import { getUserId } from "../lib/auth"
import { Skeleton } from "../components/Skeleton"

interface User {
  id: string
  email: string
  full_name: string
  role: string
}

export function UserManagement() {
  const [users, setUsers] = useState<User[]>([])
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "hr_recruiter" })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const currentUserId = getUserId()

  useEffect(() => {
    fetchUsers()
  }, [])

  async function fetchUsers() {
    try {
      const res = await apiClient.get("/auth/users")
      setUsers(res.data)
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || "Failed to load users")
    } finally {
      setLoading(false)
    }
  }

  async function createUser(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await apiClient.post("/auth/users", form)
      setForm({ email: "", password: "", full_name: "", role: "hr_recruiter" })
      toast.success("User created successfully")
      await fetchUsers()
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.message || "Failed to create user")
    } finally {
      setSubmitting(false)
    }
  }

  async function removeUser(userId: string, userName: string) {
    if (!window.confirm(`Are you sure you want to remove user "${userName}"? This action cannot be undone.`)) {
      return
    }
    setDeletingId(userId)
    try {
      await apiClient.delete(`/auth/users/${userId}`)
      toast.success(`User "${userName}" removed`)
      setUsers((prev) => prev.filter((u) => u.id !== userId))
    } catch (err: any) {
      toast.error(err.response?.data?.detail?.message || err.response?.data?.detail || err.message || "Failed to remove user")
    } finally {
      setDeletingId(null)
    }
  }

  function getRoleBadge(role: string) {
    switch (role) {
      case "admin":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">Administrator</span>
      case "hiring_manager":
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">Hiring Manager</span>
      case "hr_recruiter":
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">HR Recruiter</span>
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-heading font-semibold text-surface-text">User Management</h2>
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-heading font-semibold text-surface-text">User Management</h2>
          <p className="text-sm text-surface-muted mt-1">
            Create, assign roles, and manage team access for Recruiters, Hiring Managers, and Administrators.
          </p>
        </div>
      </div>

      {/* Create User Form */}
      <div className="bg-white p-5 rounded-xl border border-surface-border shadow-sm">
        <h3 className="text-base font-semibold text-surface-text mb-4">Add New Team Member</h3>
        <form onSubmit={createUser} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1">Full Name</label>
            <input
              placeholder="e.g. Sarah Connor"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1">Email Address</label>
            <input
              type="email"
              placeholder="sarah@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1">Password</label>
            <input
              type="password"
              placeholder="Minimum 6 characters"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-surface-muted uppercase mb-1">System Role</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full px-3 py-2 border border-surface-border rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary outline-none"
            >
              <option value="hr_recruiter">HR Recruiter (Stage 1 Triage, Upload CVs)</option>
              <option value="hiring_manager">Hiring Manager (Stage 2 Decisions, Export)</option>
              <option value="admin">Administrator (Full Access & Overrides)</option>
            </select>
          </div>

          <div className="sm:col-span-2 flex justify-end pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2.5 bg-brand-primary hover:bg-brand-primary/90 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition shadow-sm"
            >
              {submitting ? "Creating User..." : "Create User"}
            </button>
          </div>
        </form>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-surface-border shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="text-base font-semibold text-surface-text">Active Accounts</h3>
          <span className="text-xs text-surface-muted">Total: {users.length} user{users.length !== 1 ? "s" : ""}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface-page text-surface-muted uppercase text-xs">
              <tr>
                <th className="px-5 py-3">Full Name</th>
                <th className="px-5 py-3">Email Address</th>
                <th className="px-5 py-3">Assigned Role</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {users.map((u) => {
                const isSelf = currentUserId === u.id
                return (
                  <tr key={u.id} className="hover:bg-surface-page/50 transition">
                    <td className="px-5 py-3.5 font-medium text-surface-text flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-brand-primary/10 text-brand-primary font-bold text-xs flex items-center justify-center">
                        {u.full_name ? u.full_name.charAt(0).toUpperCase() : u.email.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div>{u.full_name || "—"}</div>
                        {isSelf && <span className="text-[10px] text-brand-primary font-semibold">(You)</span>}
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-surface-muted">{u.email}</td>
                    <td className="px-5 py-3.5">{getRoleBadge(u.role)}</td>
                    <td className="px-5 py-3.5 text-right">
                      {isSelf ? (
                        <span className="text-xs text-surface-muted italic">Current User</span>
                      ) : (
                        <button
                          onClick={() => removeUser(u.id, u.full_name || u.email)}
                          disabled={deletingId === u.id}
                          className="px-3 py-1.5 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-50 border border-red-200 rounded-lg transition disabled:opacity-50"
                        >
                          {deletingId === u.id ? "Removing..." : "Remove User"}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {users.length === 0 && (
          <div className="p-8 text-center text-surface-muted text-sm">No users found.</div>
        )}
      </div>
    </div>
  )
}
