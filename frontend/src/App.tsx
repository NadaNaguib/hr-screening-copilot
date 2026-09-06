import { Navigate, Route, Routes, useNavigate } from "react-router-dom"
import { useEffect, useState } from "react"
import { getRole, getToken } from "./lib/auth"
import { Sidebar } from "./layout/Sidebar"
import { Login } from "./pages/Login"
import { JobsAndCandidates } from "./pages/JobsAndCandidates"
import { CopilotChat } from "./pages/CopilotChat"
import { ReviewQueue } from "./pages/ReviewQueue"
import { Observability } from "./pages/Observability"
import { UserManagement } from "./pages/UserManagement"
import { SettingsSlaRules } from "./pages/SettingsSlaRules"

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
          <Route path="/observability" element={<Observability />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="/sla" element={<SettingsSlaRules />} />
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
