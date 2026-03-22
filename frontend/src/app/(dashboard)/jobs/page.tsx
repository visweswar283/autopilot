'use client'
import { useState } from 'react'
import { Search, Filter, MapPin, DollarSign, Clock, ExternalLink, ThumbsUp, ThumbsDown, Bookmark, Zap } from 'lucide-react'
import { clsx } from 'clsx'

const jobs = [
  { id: 1, company: 'Stripe', role: 'Senior Software Engineer', location: 'San Francisco, CA', remote: true, salary: '$180k–$240k', score: 96, portal: 'LinkedIn', posted: '2h ago', tags: ['Go', 'Distributed Systems', 'Payments'] },
  { id: 2, company: 'Vercel', role: 'Staff Frontend Engineer', location: 'Remote', remote: true, salary: '$200k–$260k', score: 91, portal: 'Greenhouse', posted: '4h ago', tags: ['React', 'Next.js', 'TypeScript'] },
  { id: 3, company: 'Linear', role: 'Full Stack Engineer', location: 'Remote', remote: true, salary: '$160k–$210k', score: 88, portal: 'Lever', posted: '6h ago', tags: ['TypeScript', 'GraphQL', 'PostgreSQL'] },
  { id: 4, company: 'Figma', role: 'Software Engineer, Platform', location: 'New York, NY', remote: false, salary: '$170k–$230k', score: 84, portal: 'Workday', posted: '1d ago', tags: ['C++', 'WebAssembly', 'React'] },
  { id: 5, company: 'Notion', role: 'Backend Engineer', location: 'Remote', remote: true, salary: '$155k–$205k', score: 79, portal: 'LinkedIn', posted: '1d ago', tags: ['Node.js', 'PostgreSQL', 'Redis'] },
  { id: 6, company: 'Retool', role: 'Senior Engineer', location: 'San Francisco, CA', remote: false, salary: '$175k–$225k', score: 76, portal: 'Greenhouse', posted: '2d ago', tags: ['React', 'Python', 'AWS'] },
]

const scoreColor = (s: number) =>
  s >= 90 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25' :
  s >= 75 ? 'text-blue-400 bg-blue-500/10 border-blue-500/25' :
  'text-yellow-400 bg-yellow-500/10 border-yellow-500/25'

export default function JobsPage() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  const filtered = jobs.filter(j =>
    (filter === 'remote' ? j.remote : true) &&
    (j.role.toLowerCase().includes(search.toLowerCase()) || j.company.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div className="p-8 animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Job Feed</h1>
          <p className="text-slate-400 mt-1">AI-scored jobs matched to your profile</p>
        </div>
        <div className="flex items-center gap-2 glass-card px-3 py-2">
          <Zap size={14} className="text-brand-400" />
          <span className="text-sm text-slate-300">{jobs.length} new matches today</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
          <input className="input-field pl-11" placeholder="Search by role or company..."
            value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex gap-2">
          {['all', 'remote', 'onsite'].map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={clsx('px-4 py-2.5 rounded-xl text-sm font-medium transition-all border capitalize',
                filter === f ? 'bg-brand-500/15 text-brand-400 border-brand-500/30' : 'text-slate-400 border-white/10 hover:border-white/20 hover:text-white')}>
              {f}
            </button>
          ))}
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-white/10 text-slate-400 hover:text-white transition-all text-sm">
          <Filter size={14} /> Filters
        </button>
      </div>

      {/* Job cards */}
      <div className="space-y-3">
        {filtered.map((job) => (
          <div key={job.id} className="glass-card p-5 hover:border-brand-500/30 transition-all duration-300 group cursor-pointer">
            <div className="flex items-start gap-4">
              {/* Company logo placeholder */}
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-600/30 to-purple-600/30 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-lg">{job.company[0]}</span>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-white font-semibold text-base group-hover:text-brand-300 transition-colors">{job.role}</h3>
                    <p className="text-slate-400 text-sm mt-0.5">{job.company} · {job.portal}</p>
                  </div>
                  <div className={`badge border flex-shrink-0 text-sm font-bold px-3 py-1 ${scoreColor(job.score)}`}>
                    {job.score}% match
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 mt-3 text-sm text-slate-400">
                  <span className="flex items-center gap-1.5"><MapPin size={13} /> {job.location}</span>
                  {job.remote && <span className="badge bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Remote</span>}
                  <span className="flex items-center gap-1.5"><DollarSign size={13} /> {job.salary}</span>
                  <span className="flex items-center gap-1.5"><Clock size={13} /> {job.posted}</span>
                </div>

                <div className="flex flex-wrap gap-2 mt-3">
                  {job.tags.map((tag) => (
                    <span key={tag} className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-300 text-xs">{tag}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-white/5">
              <button className="btn-ghost flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300">
                <ThumbsDown size={14} /> Skip
              </button>
              <button className="btn-ghost flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300">
                <Bookmark size={14} /> Save
              </button>
              <button className="btn-ghost flex items-center gap-1.5 text-sm text-slate-400 hover:text-white">
                <ExternalLink size={14} /> View
              </button>
              <button className="btn-primary flex items-center gap-2 text-sm py-2 px-4">
                <ThumbsUp size={14} /> Approve
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
