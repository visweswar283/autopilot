'use client'
import { useState, useCallback } from 'react'
import { Briefcase, Send, TrendingUp, Trophy, ArrowUpRight, Clock, Zap, BarChart2, CheckCircle2, X } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useAuthStore } from '@/store/auth'
import { useEventStream, StreamEvent } from '@/hooks/useEventStream'

const activityData = [
  { day: 'Mon', applications: 4, responses: 1 },
  { day: 'Tue', applications: 8, responses: 2 },
  { day: 'Wed', applications: 5, responses: 1 },
  { day: 'Thu', applications: 12, responses: 3 },
  { day: 'Fri', applications: 9, responses: 2 },
  { day: 'Sat', applications: 3, responses: 1 },
  { day: 'Sun', applications: 7, responses: 2 },
]

const recentJobs = [
  { company: 'Stripe', role: 'Senior Software Engineer', status: 'applied', score: 94, time: '2h ago', portal: 'LinkedIn' },
  { company: 'Vercel', role: 'Staff Engineer', status: 'interview', score: 88, time: '5h ago', portal: 'Greenhouse' },
  { company: 'Linear', role: 'Frontend Engineer', status: 'applied', score: 91, time: '1d ago', portal: 'Workday' },
  { company: 'Notion', role: 'Full Stack Engineer', status: 'viewed', score: 79, time: '1d ago', portal: 'LinkedIn' },
  { company: 'Figma', role: 'Software Engineer', status: 'queued', score: 85, time: '2d ago', portal: 'Lever' },
]

const statusConfig: Record<string, { label: string; color: string }> = {
  applied:   { label: 'Applied',    color: 'bg-blue-500/15 text-blue-400 border-blue-500/25' },
  interview: { label: 'Interview',  color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' },
  viewed:    { label: 'Viewed',     color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25' },
  queued:    { label: 'Queued',     color: 'bg-slate-500/15 text-slate-400 border-slate-500/25' },
  offer:     { label: 'Offer 🎉',  color: 'bg-purple-500/15 text-purple-400 border-purple-500/25' },
}

const stats = [
  { label: 'Jobs Discovered',  value: '1,284', change: '+48 today', icon: Briefcase,  color: 'text-blue-400',    bg: 'bg-blue-500/10' },
  { label: 'Applied',          value: '48',    change: '+8 today',  icon: Send,        color: 'text-indigo-400',  bg: 'bg-indigo-500/10' },
  { label: 'Response Rate',    value: '23%',   change: '+2% this week', icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { label: 'Interviews',       value: '6',     change: '2 upcoming',icon: Trophy,      color: 'text-purple-400',  bg: 'bg-purple-500/10' },
]

type Toast = { id: number; title: string; company: string; portal: string }

export default function DashboardPage() {
  const user   = useAuthStore((s) => s.user)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [liveCount, setLiveCount] = useState(0)

  const handleEvent = useCallback((event: StreamEvent) => {
    if (event.type === 'application' && event.status === 'applied' && event.job) {
      const toast: Toast = {
        id:      Date.now(),
        title:   event.job.title,
        company: event.job.company,
        portal:  event.job.portal,
      }
      setToasts((prev) => [toast, ...prev].slice(0, 5))
      setLiveCount((n) => n + 1)
      // Auto-dismiss after 6s
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== toast.id)), 6000)
    }
  }, [])

  useEventStream(handleEvent)

  return (
    <div className="p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Good morning{user?.email ? `, ${user.email.split('@')[0]}` : ''} 👋
          </h1>
          <p className="text-slate-400 mt-1">Here&apos;s what&apos;s happening with your job search.</p>
        </div>
        <div className="flex items-center gap-2 glass-card px-4 py-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-slow" />
          <span className="text-sm text-slate-300 font-medium">Autopilot active</span>
          {liveCount > 0 && (
            <span className="ml-1 bg-brand-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
              +{liveCount}
            </span>
          )}
          <Zap size={14} className="text-brand-400" />
        </div>
      </div>

      {/* Live application toasts */}
      {toasts.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
          {toasts.map((t) => (
            <div key={t.id}
              className="flex items-start gap-3 glass-card border border-emerald-500/30 px-4 py-3 rounded-xl shadow-lg animate-fade-in min-w-[280px]">
              <CheckCircle2 size={18} className="text-emerald-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">Applied: {t.title}</p>
                <p className="text-slate-400 text-xs">{t.company} · {t.portal}</p>
              </div>
              <button onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
                className="text-slate-500 hover:text-slate-300 flex-shrink-0">
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, change, icon: Icon, color, bg }) => (
          <div key={label} className="stat-card">
            <div className="flex items-start justify-between mb-4">
              <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center`}>
                <Icon size={20} className={color} />
              </div>
              <ArrowUpRight size={16} className="text-slate-600" />
            </div>
            <p className="text-3xl font-bold text-white mb-1">{value}</p>
            <p className="text-sm text-slate-400">{label}</p>
            <p className="text-xs text-emerald-400 mt-1 font-medium">{change}</p>
          </div>
        ))}
      </div>

      {/* Chart + Recent */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Chart */}
        <div className="xl:col-span-3 glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-white font-semibold flex items-center gap-2">
                <BarChart2 size={18} className="text-brand-400" /> Weekly Activity
              </h2>
              <p className="text-slate-500 text-sm mt-0.5">Applications vs responses</p>
            </div>
            <span className="text-xs text-slate-500 glass-card px-3 py-1">Last 7 days</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={activityData}>
              <defs>
                <linearGradient id="appGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="respGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="day" stroke="#475569" tick={{ fontSize: 12 }} />
              <YAxis stroke="#475569" tick={{ fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#12122a', border: '1px solid rgba(99,102,241,0.2)', borderRadius: '12px', color: '#e2e8f0' }} />
              <Area type="monotone" dataKey="applications" stroke="#6366f1" strokeWidth={2} fill="url(#appGrad)" name="Applied" />
              <Area type="monotone" dataKey="responses" stroke="#10b981" strokeWidth={2} fill="url(#respGrad)" name="Responses" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Recent Applications */}
        <div className="xl:col-span-2 glass-card p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-white font-semibold">Recent Applications</h2>
            <a href="/applications" className="text-xs text-brand-400 hover:text-brand-300 transition-colors">View all</a>
          </div>
          <div className="space-y-3">
            {recentJobs.map((job) => (
              <div key={job.company + job.role} className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-600/30 to-purple-600/30 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">{job.company[0]}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium truncate">{job.role}</p>
                  <p className="text-slate-500 text-xs">{job.company} · {job.portal}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <span className={`badge border ${statusConfig[job.status]?.color}`}>
                    {statusConfig[job.status]?.label}
                  </span>
                  <p className="text-slate-600 text-[10px] mt-1 flex items-center gap-1 justify-end">
                    <Clock size={9} /> {job.time}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
