import axios from "axios"
import toast from "react-hot-toast"

declare module "axios" {
  export interface AxiosRequestConfig {
    silent?: boolean
  }
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const data = error.response?.data
    const detail = data?.detail
    const message = typeof detail === "string" ? detail : detail?.message || data?.message || error.message

    if (status === 401) {
      localStorage.removeItem("token")
      localStorage.removeItem("role")
      window.location.href = "/login"
      return Promise.reject(new Error(message || "Session expired"))
    }

    const config = error.config as import("axios").AxiosRequestConfig | undefined
    const silent = config?.silent === true

    if (!silent) {
      if (status >= 500 || !status) {
        toast.error(message || "System error. Please try again later.")
      } else if (status === 422 && data?.detail) {
        const validation = Array.isArray(data.detail)
          ? data.detail.map((err: any) => `${err.loc?.join(".") || "field"}: ${err.msg}`).join("; ")
          : message
        toast.error(`Validation error: ${validation}`)
      } else if (status >= 400) {
        toast.error(message || "Request failed")
      }
    }

    return Promise.reject(new Error(message || "Request failed"))
  },
)
