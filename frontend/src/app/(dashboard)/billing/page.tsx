'use client'
import { Check, Zap, Building2, User } from 'lucide-react'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

const plans = [
  {
    id: 'free', name: 'Free', price: '$0', period: '/month', current: true,
    description: 'Perfect for getting started',
    icon: User, iconColor: 'text-slate-400', iconBg: 'bg-slate-500/10',
    features: ['10 applications/day', 'LinkedIn only', 'Basic job scoring', 'Application tracking'],
    cta: 'Current Plan',
  },
  {
    id: 'pro', name: 'Pro', price: '$29', period: '/month', current: false,
    description: 'For serious job seekers',
    icon: Zap, iconColor: 'text-brand-400', iconBg: 'bg-brand-500/10',
    popular: true,
    features: ['50 applications/day', 'All portals', 'Advanced AI scoring', 'Priority queue', 'Analytics dashboard', 'Email notifications'],
    cta: 'Upgrade to Pro',
  },
  {
    id: 'team', name: 'Team', price: '$79', period: '/month', current: false,
    description: 'For teams & agencies',
    icon: Building2, iconColor: 'text-purple-400', iconBg: 'bg-purple-500/10',
    features: ['200 applications/day', 'All portals', 'AI resume tailoring', 'Cover letter gen', 'Team analytics', 'Dedicated support'],
    cta: 'Upgrade to Team',
  },
]

const usage = [
  { label: 'Applications today', used: 4, max: 10 },
  { label: 'Portals connected',  used: 1, max: 1 },
]

export default function BillingPage() {
  return (
    <div className="p-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Billing</h1>
        <p className="text-slate-400 mt-1">Manage your subscription and usage</p>
      </div>

      {/* Usage */}
      <div className="glass-card p-6 mb-8">
        <h2 className="text-white font-semibold mb-5">Current Usage — Free Plan</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {usage.map(({ label, used, max }) => (
            <div key={label}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-300 text-sm">{label}</span>
                <span className="text-white text-sm font-medium">{used} / {max}</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2">
                <div className={clsx('h-2 rounded-full transition-all', used / max > 0.8 ? 'bg-red-500' : 'bg-brand-gradient')}
                  style={{ width: `${(used / max) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Plans */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {plans.map((plan) => {
          const Icon = plan.icon
          return (
            <div key={plan.id} className={clsx('glass-card p-6 flex flex-col relative transition-all duration-300',
              plan.popular ? 'border-brand-500/40 shadow-lg shadow-indigo-500/10' : 'hover:border-brand-500/25')}>
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="badge bg-brand-gradient text-white px-4 py-1 text-xs font-semibold shadow-lg">Most Popular</span>
                </div>
              )}

              <div className={`w-10 h-10 rounded-xl ${plan.iconBg} flex items-center justify-center mb-4`}>
                <Icon size={20} className={plan.iconColor} />
              </div>

              <h3 className="text-white font-bold text-lg">{plan.name}</h3>
              <p className="text-slate-500 text-sm mb-4">{plan.description}</p>

              <div className="flex items-end gap-1 mb-6">
                <span className="text-white text-4xl font-bold">{plan.price}</span>
                <span className="text-slate-500 text-sm mb-1">{plan.period}</span>
              </div>

              <ul className="space-y-3 flex-1 mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2.5 text-sm text-slate-300">
                    <div className="w-4 h-4 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center flex-shrink-0">
                      <Check size={9} className="text-brand-400" />
                    </div>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => !plan.current && toast.success(`Upgrading to ${plan.name}...`)}
                className={clsx('w-full py-3 rounded-xl font-semibold text-sm transition-all',
                  plan.current ? 'bg-white/5 border border-white/10 text-slate-500 cursor-default' :
                  plan.popular ? 'btn-primary' : 'border border-brand-500/30 text-brand-400 hover:bg-brand-500/10')}>
                {plan.cta}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
