import { useState, useEffect } from "react"
import { X, Download, Copy, Check, FileText, User, Briefcase, Award, Sparkles, ExternalLink, Eye } from "lucide-react"
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
  const [activeTab, setActiveTab] = useState<"pdf" | "text">("pdf")
  const [pdfLoading, setPdfLoading] = useState(true)
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  const [pdfError, setPdfError] = useState(false)

  useEffect(() => {
    if (!isOpen || !candidateId) {
      setData(null)
      setActiveTab("pdf")
      setPdfLoading(true)
      setPdfError(false)
      return
    }

    let isMounted = true
    setLoading(true)
    setPdfLoading(true)

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

  // Fetch the CV document as an authenticated blob so the request carries the
  // user's Bearer token. Native iframe / window.open / anchor navigation cannot
  // attach the Authorization header, which previously caused `missing_token`.
  useEffect(() => {
    if (!isOpen || !candidateId) {
      setPdfBlobUrl(null)
      setPdfError(false)
      return
    }

    let isMounted = true
    let objectUrl: string | null = null
    setPdfError(false)
    setPdfLoading(true)

    apiClient
      .get(`/candidates/${candidateId}/cv/pdf`, { responseType: "blob", silent: true })
      .then((res) => {
        if (!isMounted) return
        objectUrl = URL.createObjectURL(res.data)
        setPdfBlobUrl(objectUrl)
      })
      .catch((err) => {
        if (!isMounted) return
        setPdfBlobUrl(null)
        setPdfError(true)
        setPdfLoading(false)
        toast.error(
          err.response?.data?.message || err.message || "Failed to load the original CV document",
        )
      })

    return () => {
      isMounted = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
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

  const handleDownloadCv = () => {
    if (!pdfBlobUrl) {
      toast.error("The CV document is still loading. Please try again in a moment.")
      return
    }
    const link = document.createElement("a")
    link.href = pdfBlobUrl
    link.download = `${(data?.full_name || candidateName || "Candidate").replace(/\s+/g, "_")}_CV.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    toast.success("Downloading CV...")
  }

  const handleOpenCvNewTab = () => {
    if (!pdfBlobUrl) {
      toast.error("The CV document is still loading. Please try again in a moment.")
      return
    }
    window.open(pdfBlobUrl, "_blank", "noopener,noreferrer")
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 md:p-6 animate-in fade-in duration-200">
      <div
        className="bg-white rounded-2xl shadow-2xl border border-surface-border w-full max-w-5xl h-[92vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between bg-surface-page/60 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-heading font-bold text-lg text-surface-text truncate">
                  {data?.full_name || candidateName || "Candidate CV"}
                </h3>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                  {data?.filename?.endsWith(".pdf") ? data.filename : `${(data?.full_name || "candidate").replace(/\s+/g, "_")}_CV.pdf`}
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs text-surface-muted mt-0.5 flex-wrap">
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

          <div className="flex items-center gap-2 shrink-0">
            {/* View Mode Switcher */}
            <div className="bg-gray-100 p-0.5 rounded-lg flex items-center border border-gray-200 text-xs mr-2">
              <button
                onClick={() => setActiveTab("pdf")}
                className={`px-3 py-1.5 rounded-md font-semibold transition flex items-center gap-1.5 ${
                  activeTab === "pdf"
                    ? "bg-white text-brand-primary shadow-2xs font-bold"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Eye className="w-3.5 h-3.5" /> Original File
              </button>
              <button
                onClick={() => setActiveTab("text")}
                className={`px-3 py-1.5 rounded-md font-semibold transition flex items-center gap-1.5 ${
                  activeTab === "text"
                    ? "bg-white text-brand-primary shadow-2xs font-bold"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <FileText className="w-3.5 h-3.5" /> Parsed Text
              </button>
            </div>

            <button
              onClick={handleOpenCvNewTab}
              className="px-3 py-1.5 border border-surface-border hover:bg-surface-page text-surface-text text-xs font-semibold rounded-lg flex items-center gap-1.5 transition"
              title="Open CV in a full new browser window"
            >
              <ExternalLink className="w-3.5 h-3.5 text-indigo-600" /> Open in New Tab
            </button>
            <button
              onClick={handleDownloadCv}
              className="px-3.5 py-1.5 bg-brand-primary hover:bg-brand-primary/90 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition shadow-xs"
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
          <div className="px-6 py-2.5 bg-indigo-50/40 border-b border-surface-border/60 shrink-0">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-semibold uppercase text-indigo-900/70 flex items-center gap-1 mb-1">
                <Sparkles className="w-3 h-3 text-brand-primary" /> Verified Extracted Skills ({data.skills.length})
              </div>
              {activeTab === "text" && (
                <button
                  onClick={handleCopy}
                  className="text-xs text-indigo-700 hover:text-indigo-900 flex items-center gap-1 font-medium"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? "Copied Text" : "Copy Raw Text"}
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 max-h-16 overflow-y-auto">
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

        {/* Modal Main Content */}
        <div className="flex-1 overflow-hidden bg-slate-900/5 relative flex flex-col">
          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-surface-muted space-y-3">
              <div className="w-9 h-9 border-3 border-brand-primary/30 border-t-brand-primary rounded-full animate-spin" />
              <p className="text-sm font-medium">Retrieving original CV document…</p>
            </div>
          ) : activeTab === "pdf" ? (
            <div className="flex-1 w-full h-full relative bg-slate-100 flex flex-col">
              {pdfLoading && !pdfError && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 backdrop-blur-2xs">
                  <div className="w-8 h-8 border-3 border-brand-primary/30 border-t-brand-primary rounded-full animate-spin mb-2" />
                  <span className="text-xs font-medium text-slate-600">Rendering original CV document...</span>
                </div>
              )}
              {pdfBlobUrl ? (
                <iframe
                  key={`pdf-${candidateId}`}
                  src={`${pdfBlobUrl}#toolbar=1&navpanes=0`}
                  className="w-full h-full border-none flex-1"
                  title="Candidate Original CV"
                  onLoad={() => setPdfLoading(false)}
                />
              ) : (
                pdfError && (
                  <div className="flex-1 flex flex-col items-center justify-center text-surface-muted space-y-2">
                    <FileText className="w-8 h-8 text-surface-disabled" />
                    <p className="text-sm font-medium">Unable to load the original CV document.</p>
                  </div>
                )
              )}
            </div>
          ) : (
            <div className="flex-1 p-6 overflow-y-auto bg-gray-50/70">
              <div className="bg-white rounded-xl border border-surface-border p-6 shadow-xs max-w-4xl mx-auto">
                <div className="flex items-center justify-between text-xs text-surface-muted border-b border-surface-border pb-3 mb-4 font-mono">
                  <span>DOCUMENT: {data?.filename || "CV.pdf"}</span>
                  <span>LENGTH: {data?.raw_text?.length.toLocaleString() || 0} characters</span>
                </div>
                <pre className="text-xs sm:text-sm font-mono text-surface-text whitespace-pre-wrap leading-relaxed select-text font-normal">
                  {data?.raw_text || "No text available for this candidate."}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-surface-border flex items-center bg-white text-xs text-surface-muted shrink-0">
          <span className="flex items-center gap-2">
            <span>Candidate ID:</span>
            <span className="font-mono text-surface-text font-medium">{data?.candidate_id || candidateId}</span>
          </span>
        </div>
      </div>
    </div>
  )
}
