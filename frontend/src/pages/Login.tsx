import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { apiClient } from "../lib/apiClient"
import { setAuth } from "../lib/auth"

export function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("admin@example.com")
  const [password, setPassword] = useState("password123")
  const [error, setError] = useState("")
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    try {
      const res = await apiClient.post("/auth/login", { email, password })
      setAuth(res.data.access_token, res.data.role)
      onLogin()
      navigate("/jobs")
    } catch (err: any) {
      setError(err.message || "Login failed")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-page">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md border border-surface-border">
        <h1 className="text-2xl font-heading font-bold text-brand-primary mb-2">Domain Copilot</h1>
        <p className="text-surface-muted mb-6">Log in to your HR screening workspace.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-surface-border rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-surface-border rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>
          {error && <p className="text-sm text-semantic-danger">{error}</p>}
          <button
            type="submit"
            className="w-full px-4 py-2 bg-brand-primary text-white rounded-md hover:opacity-90"
          >
            Log in
          </button>
        </form>
      </div>
    </div>
  )
}
