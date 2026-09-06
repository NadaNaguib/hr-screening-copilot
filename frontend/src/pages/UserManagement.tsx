import { useEffect, useState } from "react"
import toast from "react-hot-toast"
import { apiClient } from "../lib/apiClient"
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

  useEffect(() => {
    fetchUsers()
  }, [])

  async function fetchUsers() {
    try {
      const res = await apiClient.get("/auth/users")
      setUsers(res.data)
    } catch (err: any) {
      toast.error(err.message || "Failed to load users")
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
      toast.success("User created")
      await fetchUsers()
    } catch (err: any) {
      toast.error(err.message || "Failed to create user")
    } finally {
      setSubmitting(false)
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
      <h2 className="text-2xl font-heading font-semibold text-surface-text">User Management</h2>
      <form onSubmit={createUser} className="bg-white p-4 rounded-lg border border-surface-border grid grid-cols-2 gap-4">
        <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="px-3 py-2 border rounded-md" required />
        <input placeholder="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="px-3 py-2 border rounded-md" required />
        <input placeholder="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="px-3 py-2 border rounded-md" required />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="px-3 py-2 border rounded-md">
          <option value="admin">Admin</option>
          <option value="hr_recruiter">HR Recruiter</option>
          <option value="hiring_manager">Hiring Manager</option>
        </select>
        <button type="submit" disabled={submitting} className="col-span-2 px-4 py-2 bg-brand-primary text-white rounded-md disabled:opacity-50">Create User</button>
      </form>
      <div className="bg-white rounded-lg border border-surface-border overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-surface-page text-surface-muted uppercase"><tr><th className="px-4 py-3">Name</th><th className="px-4 py-3">Email</th><th className="px-4 py-3">Role</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-surface-border"><td className="px-4 py-3">{u.full_name}</td><td className="px-4 py-3">{u.email}</td><td className="px-4 py-3">{u.role}</td></tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && (
          <div className="p-6 text-center text-surface-muted text-sm">No users found.</div>
        )}
      </div>
    </div>
  )
}
