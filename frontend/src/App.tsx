import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom"
import { useEffect, useState } from "react"
import { getRole, getToken, isAdmin } from "./lib/auth"
import logo from "./assets/logo.png"
import { Sidebar } from "./layout/Sidebar"
import { Menu } from "lucide-react"
import { Login } from "./pages/Login"
import { JobsAndCandidates } from "./pages/JobsAndCandidates"
import { CopilotChat } from "./pages/CopilotChat"
import { ReviewQueue } from "./pages/ReviewQueue"
import { Observability } from "./pages/Observability"
import { UserManagement } from "./pages/UserManagement"
import { SettingsSlaRules } from "./pages/SettingsSlaRules"
import { AISettings } from "./pages/AISettings"
import { ReviewerStats } from "./pages/ReviewerStats"

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
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true })
    }
  }, [token, navigate])

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setNavOpen(false)
  }, [location.pathname])

  if (!token) return null

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Mobile top bar (hidden on desktop) */}
      <header className="md:hidden sticky top-0 z-40 bg-white border-b border-surface-border flex items-center justify-between px-4 py-3 shrink-0">
        <button
          onClick={() => setNavOpen(true)}
          title="Open navigation menu"
          className="p-2 -ml-2 rounded-lg text-surface-text hover:bg-surface-page transition"
        >
          <Menu className="w-6 h-6" />
        </button>
        <img src={logo} alt="Vera" className="h-8 w-auto object-contain" />
        <span className="w-10" aria-hidden="true" />
      </header>

      <Sidebar mobileOpen={navOpen} onClose={() => setNavOpen(false)} />
      <main className="flex-1 p-4 sm:p-6 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/jobs" replace />} />
          <Route path="/jobs" element={<JobsAndCandidates />} />
          <Route path="/chat" element={<CopilotChat />} />
          <Route path="/queue" element={<ReviewQueue />} />
          <Route path="/observability" element={<RequireAdmin><Observability /></RequireAdmin>} />
          <Route path="/users" element={<RequireAdmin><UserManagement /></RequireAdmin>} />
          <Route path="/sla" element={<RequireAdmin><SettingsSlaRules /></RequireAdmin>} />
          <Route path="/ai" element={<RequireAdmin><AISettings /></RequireAdmin>} />
          <Route path="/stats" element={<ReviewerStats />} />
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
