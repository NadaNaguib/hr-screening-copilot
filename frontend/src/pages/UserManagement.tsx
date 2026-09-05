import { useEffect, useState } from "react"
import { apiClient } from "../lib/apiClient"

interface User {
  id: string
  email: string
  full_name: string
  role: string
}

export function UserManagement() {
  const [users, setUsers] = useState<User[]>([])
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "hr_recruiter" })

  useEffect(() => {
    fetchUsers()
  }, [])

  async function fetchUsers() {
    const res = await apiClient.get("/auth/users")
    setUsers(res.data)
  }

  async function createUser(e: React.FormEvent) {
    e.preventDefault()
    await apiClient.post("/auth/users", form)
    setForm({ email: "", password: "", full_name: "", role: "hr_recruiter" })
    fetchUsers()
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-semibold text-surface-text">User Management</h2>
      <form onSubmit={createUser} className="bg-white p-4 rounded-lg border border-surface-border grid grid-cols-2 gap-4">
        <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="px-3 py-2 border rounded-md" />
        <input placeholder="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="px-3 py-2 border rounded-md" />
        <input placeholder="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="px-3 py-2 border rounded-md" />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="px-3 py-2 border rounded-md">
          <option value="admin">Admin</option>
          <option value="hr_recruiter">HR Recruiter</option>
          <option value="hiring_manager">Hiring Manager</option>
        </select>
        <button type="submit" className="col-span-2 px-4 py-2 bg-brand-primary text-white rounded-md">Create User</button>
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
      </div>
    </div>
  )
}
