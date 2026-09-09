export function getToken() {
  return localStorage.getItem("token")
}

export function getRole() {
  return localStorage.getItem("role")
}

export function getUserId() {
  return localStorage.getItem("user_id")
}

export function setAuth(token: string, role: string, userId?: string) {
  localStorage.setItem("token", token)
  localStorage.setItem("role", role)
  if (userId) localStorage.setItem("user_id", userId)
}

export function clearAuth() {
  localStorage.removeItem("token")
  localStorage.removeItem("role")
  localStorage.removeItem("user_id")
}

export function isAdmin() {
  return getRole() === "admin"
}

export function isRecruiter() {
  return getRole() === "hr_recruiter"
}

export function isManager() {
  return getRole() === "hiring_manager"
}
