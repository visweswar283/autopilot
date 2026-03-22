'use client'
import { useState } from 'react'
import { Upload, FileText, Download, Star, Trash2, Plus, CheckCircle2 } from 'lucide-react'

const resumes = [
  { id: 1, name: 'Software Engineer — 2026', uploadedAt: 'Mar 10, 2026', isDefault: true,  size: '142 KB' },
  { id: 2, name: 'Full Stack — General',     uploadedAt: 'Feb 22, 2026', isDefault: false, size: '138 KB' },
]

export default function ResumePage() {
  const [dragging, setDragging] = useState(false)

  return (
    <div className="p-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Resume Manager</h1>
        <p className="text-slate-400 mt-1">Upload and manage your resume versions</p>
      </div>

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false) }}
        className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer mb-8 ${
          dragging ? 'border-brand-500 bg-brand-500/10' : 'border-white/15 hover:border-brand-500/50 hover:bg-white/3'
        }`}
      >
        <div className="w-16 h-16 rounded-2xl bg-brand-500/15 border border-brand-500/25 flex items-center justify-center mx-auto mb-4">
          <Upload size={28} className="text-brand-400" />
        </div>
        <p className="text-white font-semibold text-lg mb-1">Drop your resume here</p>
        <p className="text-slate-400 text-sm mb-5">PDF files up to 5MB</p>
        <label className="btn-primary cursor-pointer inline-flex items-center gap-2">
          <Plus size={16} /> Choose File
          <input type="file" accept=".pdf" className="hidden" />
        </label>
      </div>

      {/* Resume list */}
      <div className="space-y-3">
        {resumes.map((resume) => (
          <div key={resume.id} className="glass-card p-5 flex items-center gap-4 hover:border-brand-500/30 transition-all">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
              <FileText size={22} className="text-blue-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-white font-semibold">{resume.name}</p>
                {resume.isDefault && (
                  <span className="badge bg-brand-500/15 text-brand-400 border border-brand-500/25 flex items-center gap-1">
                    <CheckCircle2 size={10} /> Default
                  </span>
                )}
              </div>
              <p className="text-slate-500 text-sm mt-0.5">{resume.uploadedAt} · {resume.size}</p>
            </div>
            <div className="flex items-center gap-2">
              {!resume.isDefault && (
                <button className="btn-ghost text-sm flex items-center gap-1.5 text-slate-500">
                  <Star size={14} /> Set default
                </button>
              )}
              <button className="btn-ghost text-sm flex items-center gap-1.5 text-slate-400">
                <Download size={14} /> Download
              </button>
              <button className="btn-ghost text-sm flex items-center gap-1.5 text-red-500/70 hover:text-red-400">
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="mt-8 glass-card p-5 border-brand-500/20">
        <p className="text-sm text-slate-300 font-medium mb-1">📌 About resume tailoring</p>
        <p className="text-sm text-slate-500">
          AI resume tailoring per job description is coming in Phase 7 (Pro tier). For now, your default resume is used for all applications.
        </p>
      </div>
    </div>
  )
}
