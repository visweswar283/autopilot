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
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      const { data } = await api.post('/auth/register', { email, password })
      setAuth(data.user, data.tokens.access_token)
      toast.success('Account created! Welcome to ApplyPilot 🚀')
      router.push('/dashboard')
    } catch {
      toast.error('Email already registered')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] bg-brand-600/15 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-8 items-center animate-slide-up relative z-10">
        {/* Left — value prop */}
        <div className="hidden md:block">
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
          <div className="flex items-center gap-3 justify-center mb-8 md:hidden">
            <div className="w-10 h-10 rounded-xl bg-brand-gradient flex items-center justify-center">
              <Zap size={20} className="text-white" />
            </div>
            <span className="text-2xl font-bold text-white">ApplyPilot</span>
          </div>

          <div className="glass-card p-8">
            <div className="mb-7">
              <h1 className="text-2xl font-bold text-white mb-1">Create your account</h1>
              <p className="text-slate-400 text-sm">Free forever · No credit card needed</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                <input type="email" className="input-field" placeholder="you@example.com"
                  value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
                <div className="relative">
                  <input type={showPw ? 'text' : 'password'} className="input-field pr-12"
                    placeholder="Min. 8 characters" value={password}
                    onChange={(e) => setPassword(e.target.value)} required />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                    {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {password && (
                  <div className="mt-2 flex gap-1">
                    {[...Array(4)].map((_, i) => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${password.length > i * 2 ? 'bg-brand-500' : 'bg-white/10'}`} />
                    ))}
                  </div>
                )}
              </div>

              <button type="submit" disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2">
                {loading ? <Loader2 size={18} className="animate-spin" /> : <>Get started free <ArrowRight size={18} /></>}
              </button>
            </form>

            <div className="flex items-center gap-4 my-6">
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
