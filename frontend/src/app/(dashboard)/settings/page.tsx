'use client'
import { useState } from 'react'
import { Save, Plus, Trash2, Eye, EyeOff, Linkedin, Globe, CheckCircle2, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'

const portals = [
  { id: 'linkedin',   label: 'LinkedIn',   color: 'bg-blue-600',   connected: true },
  { id: 'workday',    label: 'Workday',    color: 'bg-red-600',    connected: false },
  { id: 'greenhouse', label: 'Greenhouse', color: 'bg-green-600',  connected: false },
  { id: 'lever',      label: 'Lever',      color: 'bg-orange-600', connected: false },
]

export default function SettingsPage() {
  const [roles, setRoles] = useState(['Software Engineer', 'Full Stack Engineer', 'Backend Engineer'])
  const [locations, setLocations] = useState(['Remote', 'San Francisco, CA', 'New York, NY'])
  const [minSalary, setMinSalary] = useState('150000')
  const [newRole, setNewRole] = useState('')
  const [newLocation, setNewLocation] = useState('')
  const [showPw, setShowPw] = useState<Record<string, boolean>>({})
  const [autoApply, setAutoApply] = useState(true)
  const [threshold, setThreshold] = useState(80)

  return (
    <div className="p-8 animate-fade-in max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 mt-1">Configure your job search preferences</p>
      </div>

      {/* Job preferences */}
      <section className="glass-card p-6 mb-5">
        <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
          <Globe size={16} className="text-brand-400" /> Job Preferences
        </h2>

        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Target Roles</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {roles.map((r) => (
                <span key={r} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-500/15 border border-brand-500/25 text-brand-300 text-sm">
                  {r}
                  <button onClick={() => setRoles(roles.filter(x => x !== r))} className="text-brand-500 hover:text-red-400 transition-colors">
                    <XCircle size={13} />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input className="input-field flex-1" placeholder="Add a target role..." value={newRole} onChange={(e) => setNewRole(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && newRole.trim()) { setRoles([...roles, newRole.trim()]); setNewRole('') }}} />
              <button onClick={() => { if (newRole.trim()) { setRoles([...roles, newRole.trim()]); setNewRole('') }}}
                className="px-4 py-2.5 rounded-xl bg-brand-500/15 border border-brand-500/30 text-brand-400 hover:bg-brand-500/25 transition-all">
                <Plus size={16} />
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Preferred Locations</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {locations.map((l) => (
                <span key={l} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-slate-300 text-sm">
                  {l}
                  <button onClick={() => setLocations(locations.filter(x => x !== l))} className="text-slate-500 hover:text-red-400 transition-colors">
                    <XCircle size={13} />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input className="input-field flex-1" placeholder="Add a location..." value={newLocation} onChange={(e) => setNewLocation(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && newLocation.trim()) { setLocations([...locations, newLocation.trim()]); setNewLocation('') }}} />
              <button onClick={() => { if (newLocation.trim()) { setLocations([...locations, newLocation.trim()]); setNewLocation('') }}}
                className="px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10 transition-all">
                <Plus size={16} />
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Minimum Salary (USD/year)</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm">$</span>
              <input type="number" className="input-field pl-8" value={minSalary} onChange={(e) => setMinSalary(e.target.value)} />
            </div>
          </div>
        </div>
      </section>

      {/* Auto-apply */}
      <section className="glass-card p-6 mb-5">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <CheckCircle2 size={16} className="text-brand-400" /> Auto-Apply Rules
          </h2>
          <button onClick={() => setAutoApply(!autoApply)}
            className={`relative w-12 h-6 rounded-full transition-colors ${autoApply ? 'bg-brand-500' : 'bg-white/10'}`}>
            <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${autoApply ? 'translate-x-7' : 'translate-x-1'}`} />
          </button>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Auto-apply threshold: <span className="text-brand-400">{threshold}% match</span>
          </label>
          <input type="range" min={50} max={100} value={threshold} onChange={(e) => setThreshold(+e.target.value)}
            className="w-full accent-indigo-500" />
          <div className="flex justify-between text-xs text-slate-600 mt-1"><span>50%</span><span>100%</span></div>
          <p className="text-slate-500 text-xs mt-2">Only jobs scoring above {threshold}% will be auto-submitted.</p>
        </div>
      </section>

      {/* Portal credentials */}
      <section className="glass-card p-6 mb-6">
        <h2 className="text-white font-semibold mb-5 flex items-center gap-2">
          <Linkedin size={16} className="text-brand-400" /> Portal Credentials
        </h2>
        <div className="space-y-3">
          {portals.map((p) => (
            <div key={p.id} className="flex items-center gap-4 p-4 rounded-xl bg-white/3 border border-white/8 hover:border-white/15 transition-all">
              <div className={`w-8 h-8 rounded-lg ${p.color} flex items-center justify-center flex-shrink-0`}>
                <span className="text-white text-xs font-bold">{p.label[0]}</span>
              </div>
              <div className="flex-1">
                <p className="text-white text-sm font-medium">{p.label}</p>
                <p className="text-slate-500 text-xs">{p.connected ? 'Connected' : 'Not connected'}</p>
              </div>
              {p.connected
                ? <span className="badge bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1"><CheckCircle2 size={10} /> Active</span>
                : <button className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"><Plus size={12} /> Connect</button>
              }
            </div>
          ))}
        </div>
      </section>

      <button onClick={() => toast.success('Settings saved!')} className="btn-primary flex items-center gap-2">
        <Save size={16} /> Save Settings
      </button>
    </div>
  )
}
