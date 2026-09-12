import { NavLink } from "react-router-dom"
import { clearAuth, getRole } from "../lib/auth"
import logo from "../assets/logo.png"

export function Sidebar() {
  const role = getRole()

  const links: { to: string; label: string; roles: string[] }[] = [
    { to: "/jobs", label: "Jobs & Candidates", roles: ["admin", "hr_recruiter", "hiring_manager"] },
    { to: "/chat", label: "Copilot Chat", roles: ["admin", "hr_recruiter", "hiring_manager"] },
    { to: "/queue", label: "Review Queue", roles: ["admin", "hr_recruiter", "hiring_manager"] },
    { to: "/stats", label: "Reviewer Stats", roles: ["admin", "hr_recruiter", "hiring_manager"] },
    { to: "/observability", label: "Observability", roles: ["admin"] },
    { to: "/ai", label: "AI Control Panel", roles: ["admin"] },
    { to: "/users", label: "User Management", roles: ["admin"] },
    { to: "/sla", label: "SLA Rules", roles: ["admin"] },
  ]

  return (
    <aside className="w-64 bg-white border-r border-surface-border flex flex-col">
      <div className="p-6 border-b border-surface-border">
        <img src={logo} alt="Vera — AI-Powered Talent Screening" className="h-8 w-auto" />
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {links
          .filter((l) => l.roles.includes(role || ""))
          .map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `block px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brand-primary text-white"
                    : "text-surface-text hover:bg-surface-page"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
      </nav>
      <div className="p-4 border-t border-surface-border">
        <div className="text-xs text-surface-muted mb-2">Role: <span className="font-semibold">{role}</span></div>
        <button
          onClick={() => {
            clearAuth()
            window.location.href = "/login"
          }}
          className="w-full px-4 py-2 text-sm border border-surface-border rounded-md hover:bg-surface-page"
        >
          Log out
        </button>
      </div>
    </aside>
  )
}
