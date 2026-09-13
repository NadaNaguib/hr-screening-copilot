import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Eye, EyeOff } from "lucide-react"
import { apiClient } from "../lib/apiClient"
import { setAuth } from "../lib/auth"
import logo from "../assets/logo.png"

export function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("admin@example.com")
  const [password, setPassword] = useState("password123")
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState("")
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    // Clear any previous error only when the user submits again; otherwise the
    // "Invalid email or password" banner would flash and vanish on its own.
    setError("")
    try {
      // `silent` suppresses the global toast so the inline banner below is the
      // single source of feedback for failed logins.
      const res = await apiClient.post("/auth/login", { email, password }, { silent: true })
      setAuth(res.data.access_token, res.data.role, res.data.user_id)
      onLogin()
      navigate("/jobs")
    } catch (err: any) {
      setError(err.message || "Login failed")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-page">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md border border-surface-border">
        <img src={logo} alt="Vera — AI-Powered Talent Screening" className="h-12 w-auto mb-2" />
        <p className="text-surface-muted mb-6">Log in to your Talent Screening workspace.</p>
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
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 pr-10 border border-surface-border rounded-md focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide Password" : "Show Password"}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-surface-muted hover:text-surface-text focus:outline-none"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
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
