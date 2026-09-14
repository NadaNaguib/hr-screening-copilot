import { NavLink } from "react-router-dom"
import { clearAuth, getRole } from "../lib/auth"
import logo from "../assets/logo.png"
import { X } from "lucide-react"

interface SidebarProps {
  /** Controls the mobile drawer (desktop sidebar is always visible). */
  mobileOpen: boolean
  onClose: () => void
}

export function Sidebar({ mobileOpen, onClose }: SidebarProps) {
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

  const content = (
    <>
      <div className="p-6 border-b border-surface-border flex items-center justify-between">
        <img src={logo} alt="Vera — AI-Powered Talent Screening" className="h-10 w-auto" />
        <button
          onClick={onClose}
          title="Close menu"
          className="md:hidden p-1.5 rounded-lg text-surface-muted hover:text-surface-text hover:bg-surface-page transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {links
          .filter((l) => l.roles.includes(role || ""))
          .map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              onClick={onClose}
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
    </>
  )

  return (
    <>
      {/* Desktop sidebar (hidden below the `md` breakpoint) */}
      <aside className="hidden md:flex w-64 bg-white border-r border-surface-border flex-col shrink-0">
        {content}
      </aside>

      {/* Mobile drawer overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-xs"
            onClick={onClose}
            aria-hidden="true"
          />
          <aside className="absolute inset-y-0 left-0 w-64 bg-white border-r border-surface-border flex flex-col shadow-xl animate-in slide-in-from-left duration-200">
            {content}
          </aside>
        </div>
      )}
    </>
  )
}
