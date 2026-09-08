import { Navigate, Route, Routes, useNavigate } from "react-router-dom"
import { useEffect, useState } from "react"
import { getRole, getToken, isAdmin } from "./lib/auth"
import { Sidebar } from "./layout/Sidebar"
import { Login } from "./pages/Login"
import { JobsAndCandidates } from "./pages/JobsAndCandidates"
import { CopilotChat } from "./pages/CopilotChat"
import { ReviewQueue } from "./pages/ReviewQueue"
import { Observability } from "./pages/Observability"
import { UserManagement } from "./pages/UserManagement"
import { SettingsSlaRules } from "./pages/SettingsSlaRules"
import { AISettings } from "./pages/AISettings"

function RequireAdmin({ children }: { children: JSX.Element }) {
  const navigate = useNavigate()
  const admin = isAdmin()

  useEffect(() => {
    if (!admin) {
      navigate("/jobs", { replace: true })
    }
  }, [admin, navigate])

  return admin ? children : null
}

function PrivateLayout() {
  const navigate = useNavigate()
  const token = getToken()

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true })
    }
  }, [token, navigate])

  if (!token) return null

  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/jobs" replace />} />
          <Route path="/jobs" element={<JobsAndCandidates />} />
          <Route path="/chat" element={<CopilotChat />} />
          <Route path="/queue" element={<ReviewQueue />} />
          <Route path="/observability" element={<RequireAdmin><Observability /></RequireAdmin>} />
          <Route path="/users" element={<RequireAdmin><UserManagement /></RequireAdmin>} />
          <Route path="/sla" element={<RequireAdmin><SettingsSlaRules /></RequireAdmin>} />
          <Route path="/ai" element={<RequireAdmin><AISettings /></RequireAdmin>} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  const [_role, setRole] = useState<string | null>(getRole())

  useEffect(() => {
    const handler = () => setRole(getRole())
    window.addEventListener("storage", handler)
    return () => window.removeEventListener("storage", handler)
  }, [])

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={() => setRole(getRole())} />} />
      <Route path="/*" element={<PrivateLayout />} />
    </Routes>
  )
}
