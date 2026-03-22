'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard, Briefcase, FileText, Upload,
  Settings, CreditCard, Zap, LogOut, ChevronRight,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { clsx } from 'clsx'

const nav = [
  { href: '/dashboard',    label: 'Dashboard',     icon: LayoutDashboard },
  { href: '/jobs',         label: 'Job Feed',       icon: Briefcase },
  { href: '/applications', label: 'Applications',   icon: FileText },
  { href: '/resume',       label: 'Resume',         icon: Upload },
  { href: '/settings',     label: 'Settings',       icon: Settings },
  { href: '/billing',      label: 'Billing',        icon: CreditCard },
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useAuthStore()

  function handleLogout() {
    logout()
    router.push('/login')
  }

  return (
    <aside className="w-64 min-h-screen bg-dark-800 border-r border-[rgba(99,102,241,0.12)] flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-[rgba(99,102,241,0.12)]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-gradient flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <span className="text-white font-bold text-lg leading-none">ApplyPilot</span>
            <p className="text-[10px] text-brand-400 font-medium tracking-wider uppercase mt-0.5">Autopilot</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link key={href} href={href}
              className={clsx('nav-item', active && 'active')}>
              <Icon size={18} />
              <span>{label}</span>
              {active && <ChevronRight size={14} className="ml-auto text-brand-400" />}
            </Link>
          )
        })}
      </nav>

      {/* Plan badge */}
      <div className="p-4">
        <div className="glass-card p-4 mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Free Plan</span>
            <span className="badge bg-brand-500/15 text-brand-400 border border-brand-500/25">Active</span>
          </div>
          <div className="text-xs text-slate-500 mb-3">10 / 100 applications used</div>
          <div className="w-full bg-white/10 rounded-full h-1.5">
            <div className="bg-brand-gradient h-1.5 rounded-full" style={{ width: '10%' }} />
          </div>
          <Link href="/billing" className="mt-3 text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1 transition-colors">
            Upgrade to Pro <ChevronRight size={12} />
          </Link>
        </div>

        {/* User + logout */}
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-brand-gradient flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-bold">
              {user?.email?.[0]?.toUpperCase() ?? 'U'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">{user?.email ?? 'User'}</p>
            <p className="text-slate-500 text-xs capitalize">{user?.plan ?? 'free'} plan</p>
          </div>
          <button onClick={handleLogout} className="text-slate-500 hover:text-red-400 transition-colors p-1" title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
