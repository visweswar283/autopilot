'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, Zap, ArrowRight, Loader2, Check } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

const perks = ['100 free applications/month', 'LinkedIn & Workday support', 'AI job scoring', 'Real-time tracking']

export default function RegisterPage() {
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [form, setForm] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    mobile_number: '',
    address: '',
    linkedin_url: '',
    portfolio_url: '',
    github_url: '',
  })
  const [showPw, setShowPw] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)

  function set(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    if (form.password !== form.confirmPassword) { toast.error('Passwords do not match'); return }
    setLoading(true)
    try {
      const { data } = await api.post('/auth/register', {
        email: form.email,
        password: form.password,
        mobile_number: form.mobile_number,
        address: form.address,
        linkedin_url: form.linkedin_url,
        portfolio_url: form.portfolio_url,
        github_url: form.github_url,
      })
      setAuth(data.user, data.tokens.access_token)
      toast.success('Account created! Welcome to ApplyPilot 🚀')
      router.push('/dashboard')
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Registration failed'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const pwStrength = Math.min(4, Math.floor(form.password.length / 3))
  const strengthColor = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-green-500']

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] bg-brand-600/15 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-8 items-start animate-slide-up relative z-10">
        {/* Left — value prop */}
        <div className="hidden md:block pt-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-brand-gradient flex items-center justify-center shadow-lg shadow-indigo-500/40">
              <Zap size={20} className="text-white" />
            </div>
            <span className="text-2xl font-bold text-white">ApplyPilot</span>
          </div>
          <h2 className="text-4xl font-bold text-white leading-tight mb-4">
            Apply to hundreds of jobs
            <span className="text-transparent bg-clip-text bg-brand-gradient"> automatically</span>
          </h2>
          <p className="text-slate-400 mb-8 leading-relaxed">
            Stop spending hours on job applications. ApplyPilot discovers jobs, scores them by fit, and applies on your behalf — while you focus on what matters.
          </p>
          <div className="space-y-3">
            {perks.map((perk) => (
              <div key={perk} className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-brand-500/20 border border-brand-500/40 flex items-center justify-center flex-shrink-0">
                  <Check size={11} className="text-brand-400" />
                </div>
                <span className="text-slate-300 text-sm">{perk}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right — form */}
        <div>
          <div className="flex items-center gap-3 justify-center mb-6 md:hidden">
            <div className="w-10 h-10 rounded-xl bg-brand-gradient flex items-center justify-center">
              <Zap size={20} className="text-white" />
            </div>
            <span className="text-2xl font-bold text-white">ApplyPilot</span>
          </div>

          <div className="glass-card p-8">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-white mb-1">Create your account</h1>
              <p className="text-slate-400 text-sm">Free forever · No credit card needed</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Email <span className="text-red-400">*</span></label>
                <input type="email" className="input-field" placeholder="you@example.com"
                  value={form.email} onChange={(e) => set('email', e.target.value)} required />
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Password <span className="text-red-400">*</span></label>
                <div className="relative">
                  <input type={showPw ? 'text' : 'password'} className="input-field pr-12"
                    placeholder="Min. 8 characters" value={form.password}
                    onChange={(e) => set('password', e.target.value)} required />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                    {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {form.password && (
                  <div className="mt-2 flex gap-1">
                    {[0,1,2,3].map((i) => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i < pwStrength ? strengthColor[pwStrength - 1] : 'bg-white/10'}`} />
                    ))}
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password <span className="text-red-400">*</span></label>
                <div className="relative">
                  <input type={showConfirm ? 'text' : 'password'} className="input-field pr-12"
                    placeholder="Re-enter password" value={form.confirmPassword}
                    onChange={(e) => set('confirmPassword', e.target.value)} required />
                  <button type="button" onClick={() => setShowConfirm(!showConfirm)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                    {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {form.confirmPassword && form.password !== form.confirmPassword && (
                  <p className="text-red-400 text-xs mt-1">Passwords do not match</p>
                )}
              </div>

              {/* Mobile Number */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Mobile Number <span className="text-red-400">*</span></label>
                <input type="tel" className="input-field" placeholder="+1 (555) 000-0000"
                  value={form.mobile_number} onChange={(e) => set('mobile_number', e.target.value)} required />
              </div>

              {/* Address */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Address <span className="text-red-400">*</span></label>
                <input type="text" className="input-field" placeholder="City, State, Country"
                  value={form.address} onChange={(e) => set('address', e.target.value)} required />
              </div>

              {/* Optional URLs */}
              <div className="pt-1">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Optional — add now or later in settings</p>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1.5">LinkedIn URL</label>
                    <input type="url" className="input-field" placeholder="https://linkedin.com/in/yourname"
                      value={form.linkedin_url} onChange={(e) => set('linkedin_url', e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1.5">Portfolio URL</label>
                    <input type="url" className="input-field" placeholder="https://yourportfolio.com"
                      value={form.portfolio_url} onChange={(e) => set('portfolio_url', e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1.5">GitHub URL</label>
                    <input type="url" className="input-field" placeholder="https://github.com/yourusername"
                      value={form.github_url} onChange={(e) => set('github_url', e.target.value)} />
                  </div>
                </div>
              </div>

              <button type="submit" disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
                {loading ? <Loader2 size={18} className="animate-spin" /> : <>Get started free <ArrowRight size={18} /></>}
              </button>
            </form>

            <div className="flex items-center gap-4 my-5">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-slate-500 text-xs">already have an account?</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>

            <Link href="/login" className="flex items-center justify-center gap-2 w-full py-3 rounded-xl border border-white/10 text-slate-300 hover:text-white hover:border-white/20 transition-all text-sm font-medium">
              Sign in instead
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
