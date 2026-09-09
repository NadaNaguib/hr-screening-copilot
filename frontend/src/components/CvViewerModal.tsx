import { useState, useEffect } from "react"
import { X, Download, Copy, Check, FileText, User, Briefcase, Award, Sparkles } from "lucide-react"
import { apiClient } from "../lib/apiClient"
import { toast } from "react-hot-toast"

interface CvViewerModalProps {
  candidateId: string | null
  candidateName?: string
  isOpen: boolean
  onClose: () => void
}

interface CvData {
  candidate_id: string
  full_name: string
  email: string
  job_id: string | null
  raw_text: string
  filename: string
  document_id: string | null
  mime_type: string
  skills: string[]
  priority: string
  years_of_experience: number
}

export function CvViewerModal({ candidateId, candidateName, isOpen, onClose }: CvViewerModalProps) {
  const [data, setData] = useState<CvData | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!isOpen || !candidateId) {
      setData(null)
      return
    }

    let isMounted = true
    setLoading(true)

    apiClient
      .get(`/candidates/${candidateId}/cv`)
      .then((res) => {
        if (isMounted) {
          setData(res.data)
        }
      })
      .catch((err) => {
        if (isMounted) {
          toast.error(err.response?.data?.message || err.message || "Failed to load candidate CV")
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [isOpen, candidateId])

  if (!isOpen) return null

  const handleCopy = () => {
    if (!data?.raw_text) return
    navigator.clipboard.writeText(data.raw_text)
    setCopied(true)
    toast.success("CV text copied to clipboard!")
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    if (!candidateId) return
    const filename = data?.filename || `${(data?.full_name || "candidate").replace(/\s+/g, "_")}_CV.txt`
    const element = document.createElement("a")
    const file = new Blob([data?.raw_text || ""], { type: "text/plain;charset=utf-8" })
    element.href = URL.createObjectURL(file)
    element.download = filename
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    toast.success(`Downloaded ${filename}`)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="bg-white rounded-2xl shadow-2xl border border-surface-border w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between bg-surface-page/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-heading font-bold text-lg text-surface-text">
                  {data?.full_name || candidateName || "Candidate CV"}
                </h3>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-gray-100 text-gray-700">
                  {data?.filename || "CV Document"}
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs text-surface-muted mt-0.5">
                {data?.email && (
                  <span className="flex items-center gap-1 font-mono">
                    <User className="w-3.5 h-3.5 text-brand-primary" /> {data.email}
                  </span>
                )}
                {data?.years_of_experience !== undefined && (
                  <span className="flex items-center gap-1">
                    <Briefcase className="w-3.5 h-3.5 text-emerald-600" />
                    {data.years_of_experience > 0 ? `${data.years_of_experience.toFixed(1)} yrs exp` : "Entry Level"}
                  </span>
                )}
                {data?.priority && (
                  <span className="flex items-center gap-1">
                    <Award className="w-3.5 h-3.5 text-amber-600" /> Priority: {data.priority}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={!data?.raw_text}
              className="px-3 py-1.5 border border-surface-border hover:bg-surface-page text-surface-text text-xs font-semibold rounded-lg flex items-center gap-1.5 transition disabled:opacity-50"
              title="Copy original CV text to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied" : "Copy Text"}
            </button>
            <button
              onClick={handleDownload}
              disabled={!data?.raw_text}
              className="px-3 py-1.5 bg-brand-primary hover:bg-brand-primary/90 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition shadow-xs disabled:opacity-50"
              title="Download original CV file"
            >
              <Download className="w-3.5 h-3.5" /> Download CV
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-surface-muted hover:text-surface-text hover:bg-surface-page rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Skills Banner */}
        {data?.skills && data.skills.length > 0 && (
          <div className="px-6 py-3 bg-indigo-50/40 border-b border-surface-border/60">
            <div className="text-[11px] font-semibold uppercase text-indigo-900/70 mb-1.5 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-brand-primary" /> Verified Extracted Skills ({data.skills.length})
            </div>
            <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
              {data.skills.map((skill, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded-md text-xs bg-white text-brand-primary border border-brand-primary/20 font-mono shadow-2xs font-medium"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Body: Full Original CV Text */}
        <div className="flex-1 p-6 overflow-y-auto bg-gray-50/50">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-surface-muted space-y-3">
              <div className="w-8 h-8 border-3 border-brand-primary/30 border-t-brand-primary rounded-full animate-spin" />
              <p className="text-sm font-medium">Retrieving original CV document…</p>
            </div>
          ) : !data?.raw_text ? (
            <div className="text-center py-16 text-surface-muted">
              <FileText className="w-12 h-12 text-surface-muted/40 mx-auto mb-2" />
              <p className="text-sm">No raw CV text available for this candidate.</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-surface-border p-6 shadow-xs">
              <div className="flex items-center justify-between text-xs text-surface-muted border-b border-surface-border pb-3 mb-4 font-mono">
                <span>FILE: {data.filename}</span>
                <span>LENGTH: {data.raw_text.length.toLocaleString()} characters</span>
              </div>
              <pre className="text-xs sm:text-sm font-mono text-surface-text whitespace-pre-wrap leading-relaxed select-text font-normal">
                {data.raw_text}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-surface-border flex items-center justify-between bg-white text-xs text-surface-muted">
          <span>Candidate ID: <span className="font-mono text-surface-text">{data?.candidate_id || candidateId}</span></span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-100 hover:bg-gray-200 text-surface-text font-medium rounded-lg transition"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  )
}
