'use client'
import { useState } from 'react'
import { Search, RotateCcw, Clock, CheckCircle2, XCircle, Eye, MessageSquare, Trophy, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'

const applications = [
  { id: 1, company: 'Stripe', role: 'Senior Software Engineer', status: 'interview', portal: 'LinkedIn', appliedAt: 'Mar 18, 2026', updatedAt: '2h ago' },
  { id: 2, company: 'Vercel', role: 'Staff Engineer', status: 'viewed', portal: 'Greenhouse', appliedAt: 'Mar 17, 2026', updatedAt: '1d ago' },
  { id: 3, company: 'Linear', role: 'Full Stack Engineer', status: 'applied', portal: 'Lever', appliedAt: 'Mar 16, 2026', updatedAt: '2d ago' },
  { id: 4, company: 'Figma', role: 'Platform Engineer', status: 'applied', portal: 'Workday', appliedAt: 'Mar 15, 2026', updatedAt: '3d ago' },
  { id: 5, company: 'Notion', role: 'Backend Engineer', status: 'rejected', portal: 'LinkedIn', appliedAt: 'Mar 12, 2026', updatedAt: '5d ago' },
  { id: 6, company: 'Retool', role: 'Senior Engineer', status: 'offer', portal: 'Greenhouse', appliedAt: 'Mar 10, 2026', updatedAt: '7d ago' },
  { id: 7, company: 'Loom', role: 'Software Engineer', status: 'applied', portal: 'Lever', appliedAt: 'Mar 9, 2026', updatedAt: '8d ago' },
]

const statusMap: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  queued:    { label: 'Queued',    icon: Clock,          color: 'text-slate-400 bg-slate-500/10 border-slate-500/20' },
  applied:   { label: 'Applied',   icon: CheckCircle2,   color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  viewed:    { label: 'Viewed',    icon: Eye,            color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' },
  interview: { label: 'Interview', icon: MessageSquare,  color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  offer:     { label: 'Offer',     icon: Trophy,         color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  rejected:  { label: 'Rejected',  icon: XCircle,        color: 'text-red-400 bg-red-500/10 border-red-500/20' },
  failed:    { label: 'Failed',    icon: AlertCircle,    color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
}

const statuses = ['all', 'applied', 'viewed', 'interview', 'offer', 'rejected']

export default function ApplicationsPage() {
  const [search, setSearch] = useState('')
  const [activeStatus, setActiveStatus] = useState('all')

  const filtered = applications.filter(a =>
    (activeStatus === 'all' || a.status === activeStatus) &&
    (a.company.toLowerCase().includes(search.toLowerCase()) || a.role.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div className="p-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Applications</h1>
        <p className="text-slate-400 mt-1">Track every application across all portals</p>
      </div>

      {/* Summary pills */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-6">
        {statuses.filter(s => s !== 'all').map((s) => {
          const count = applications.filter(a => a.status === s).length
          const cfg = statusMap[s]
          const Icon = cfg?.icon
          return (
            <button key={s} onClick={() => setActiveStatus(s === activeStatus ? 'all' : s)}
              className={clsx('glass-card p-3 text-center transition-all hover:border-brand-500/30', activeStatus === s && 'border-brand-500/40')}>
              {Icon && <Icon size={16} className={clsx('mx-auto mb-1', cfg.color.split(' ')[0])} />}
              <p className="text-white font-bold text-lg">{count}</p>
              <p className="text-slate-500 text-xs capitalize">{s}</p>
            </button>
          )
        })}
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
        <input className="input-field pl-11" placeholder="Search applications..."
          value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              <th className="text-left text-xs text-slate-500 font-medium uppercase tracking-wider px-6 py-4">Company</th>
              <th className="text-left text-xs text-slate-500 font-medium uppercase tracking-wider px-6 py-4">Role</th>
              <th className="text-left text-xs text-slate-500 font-medium uppercase tracking-wider px-6 py-4">Portal</th>
              <th className="text-left text-xs text-slate-500 font-medium uppercase tracking-wider px-6 py-4">Applied</th>
              <th className="text-left text-xs text-slate-500 font-medium uppercase tracking-wider px-6 py-4">Status</th>
              <th className="text-left text-xs text-slate-500 font-medium uppercase tracking-wider px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filtered.map((app) => {
              const cfg = statusMap[app.status]
              const Icon = cfg?.icon
              return (
                <tr key={app.id} className="hover:bg-white/3 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-600/30 to-purple-600/30 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-white text-xs font-bold">{app.company[0]}</span>
                      </div>
                      <span className="text-white font-medium text-sm">{app.company}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-slate-300 text-sm">{app.role}</td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-400 text-xs">{app.portal}</span>
                  </td>
                  <td className="px-6 py-4 text-slate-500 text-sm">{app.appliedAt}</td>
                  <td className="px-6 py-4">
                    <span className={clsx('badge border flex items-center gap-1.5 w-fit', cfg?.color)}>
                      {Icon && <Icon size={11} />} {cfg?.label}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <button className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-brand-400 transition-colors">
                      <RotateCcw size={12} /> Retry
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-16 text-slate-500">No applications found</div>
        )}
      </div>
    </div>
  )
}
