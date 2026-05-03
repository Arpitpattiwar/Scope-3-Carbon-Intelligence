import { useEffect, useState } from 'react'
import { Lock, Plus, Target, Mail, Trash2, ExternalLink } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { periodsApi, targetsApi } from '@/utils/api'
import { SectionHeader, Modal, Spinner, PageLoader } from '@/components/ui'
import { URLS } from '@/utils/urls'

export default function SettingsPage() {
  const [periods, setPeriods] = useState<any[]>([])
  const [targets, setTargets] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [periodModal, setPeriodModal] = useState(false)
  const [targetModal, setTargetModal] = useState(false)
  const [saving, setSaving] = useState(false)
  const periodForm = useForm()
  const targetForm = useForm()

  useEffect(() => { fetchAll() }, [])

  const fetchAll = async () => {
    const [p, t] = await Promise.all([periodsApi.list(), targetsApi.list()])
    setPeriods(p.data); setTargets(t.data); setLoading(false)
  }

  const onCreatePeriod = async (data: any) => {
    setSaving(true)
    try { await periodsApi.create(data); toast.success('Period created'); setPeriodModal(false); periodForm.reset(); fetchAll() }
    catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
    finally { setSaving(false) }
  }

  const onCreateTarget = async (data: any) => {
    setSaving(true)
    try {
      await targetsApi.create({ ...data, year: parseInt(data.year), target_co2e: parseFloat(data.target_co2e) })
      toast.success('Target set'); setTargetModal(false); targetForm.reset(); fetchAll()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
    finally { setSaving(false) }
  }

  const onDeleteTarget = async (id: number) => {
    if (!confirm('Delete this target?')) return
    await targetsApi.delete(id); fetchAll()
  }

  const onLock = async (id: number, label: string) => {
    if (!confirm(`Lock period "${label}"? This cannot be undone.`)) return
    await periodsApi.lock(id); toast.success(`"${label}" locked`); fetchAll()
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <SectionHeader title="Platform Settings" description="Reporting periods, targets, and configuration"/>

      {/* Reporting Periods */}
      <div className="card">
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Reporting Periods</h3>
            <p className="text-xs text-gray-500 mt-0.5">Locked periods cannot be edited — ensures audit integrity.</p>
          </div>
          <button onClick={() => setPeriodModal(true)} className="btn-secondary text-sm"><Plus size={14}/> New Period</button>
        </div>
        {loading ? <PageLoader /> : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="table-header">Label</th>
                <th className="table-header">Start</th>
                <th className="table-header">End</th>
                <th className="table-header">Status</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {periods.map((p: any) => (
                <tr key={p.id}>
                  <td className="table-cell font-medium">{p.label}</td>
                  <td className="table-cell text-sm text-gray-500">{p.period_start}</td>
                  <td className="table-cell text-sm text-gray-500">{p.period_end}</td>
                  <td className="table-cell">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${p.is_locked ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                      {p.is_locked ? <><Lock size={10}/> Locked</> : '🟢 Open'}
                    </span>
                  </td>
                  <td className="table-cell">
                    {!p.is_locked && (
                      <button onClick={() => onLock(p.id, p.label)} className="btn-danger text-xs px-3 py-1.5">
                        <Lock size={12}/> Lock
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Emission Targets */}
      <div className="card">
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Emission Reduction Targets</h3>
            <p className="text-xs text-gray-500 mt-0.5">Targets appear as reference lines on the trend chart.</p>
          </div>
          <button onClick={() => setTargetModal(true)} className="btn-secondary text-sm"><Target size={14}/> New Target</button>
        </div>
        {loading ? <PageLoader /> : targets.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">No targets set. Add one to show a reference line on the dashboard.</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="table-header">Label</th>
                <th className="table-header">Year</th>
                <th className="table-header">Target (tCO₂e)</th>
                <th className="table-header">Region</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {targets.map((t: any) => (
                <tr key={t.id}>
                  <td className="table-cell font-medium">{t.label}</td>
                  <td className="table-cell">{t.year}</td>
                  <td className="table-cell font-mono font-semibold text-brand-700">{Number(t.target_co2e).toLocaleString()} tCO₂e</td>
                  <td className="table-cell capitalize">{t.region || 'All regions'}</td>
                  <td className="table-cell">
                    <button onClick={() => onDeleteTarget(t.id)} className="p-1.5 hover:bg-red-50 text-red-400 rounded-lg transition-colors">
                      <Trash2 size={14}/>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Email / SMTP Config Guide */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-1">Email Configuration (SMTP)</h3>
        <p className="text-xs text-gray-500 mb-4">Configure SMTP in <code className="bg-gray-100 px-1 rounded">docker-compose.yml</code> to enable real email delivery for vendor invitations and record status updates.</p>
        <div className="space-y-3">
          <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
            <p className="text-xs font-semibold text-amber-800 mb-1">Gmail App Password (recommended for demo)</p>
            <ol className="text-xs text-amber-700 space-y-1 list-decimal list-inside">
              <li>Enable 2-factor auth on your Google account</li>
              <li>Go to Google Account → Security → App Passwords</li>
              <li>Create a new App Password for "Mail"</li>
              <li>Set the values below in <code className="bg-amber-100 px-1 rounded">docker-compose.yml</code></li>
            </ol>
          </div>
          <div className="p-3 bg-gray-900 rounded-xl">
            <pre className="text-xs text-green-400 font-mono whitespace-pre">{`SMTP_HOST: smtp.gmail.com
SMTP_PORT: 587
SMTP_USER: your@gmail.com
SMTP_PASSWORD: xxxx-xxxx-xxxx-xxxx`}</pre>
          </div>
          <p className="text-xs text-gray-400">
            Without SMTP configured, invitation passwords are shown in the invite modal and printed to the backend console.
          </p>
          <a href={URLS.googleAppPasswords} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline">
            <ExternalLink size={12}/> Open Google App Passwords
          </a>
        </div>
      </div>

      {/* Phase 2 — AI & Advanced Features */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-brand-100 text-brand-700 rounded-full">Phase 2 — Active</span>
          <h3 className="text-sm font-semibold text-gray-900">AI Estimation &amp; Advanced Features</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-3 bg-green-50 border border-green-100 rounded-xl">
            <p className="text-xs font-semibold text-green-800 mb-1">✅ AI Spend-Based Estimation</p>
            <p className="text-xs text-green-700">XGBoost ML model (Cat 1, 2, 13–15) + DEFRA rule-based fallback for all 15 categories. Enabled via AI_ESTIMATION_ENABLED=true in docker-compose.</p>
          </div>
          <div className="p-3 bg-green-50 border border-green-100 rounded-xl">
            <p className="text-xs font-semibold text-green-800 mb-1">✅ LSTM Emission Forecast</p>
            <p className="text-xs text-green-700">3-month forward forecast using LSTM model trained on India macro sector data. Requires ≥12 months of platform data. Visible on dashboard for all roles.</p>
          </div>
          <div className="p-3 bg-green-50 border border-green-100 rounded-xl">
            <p className="text-xs font-semibold text-green-800 mb-1">✅ Anomaly Detection</p>
            <p className="text-xs text-green-700">Autoencoder model (PR-AUC 0.70) flags outlier records on submit and CSV upload. Covers 6 of 15 categories; false-positive rate ~64% — use as advisory, not hard gate.</p>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
            <p className="text-xs font-semibold text-amber-800 mb-1">🔜 Benchmark Engine</p>
            <p className="text-xs text-amber-700">Compare emission intensity against industry average. Configure sector benchmarks and intensity thresholds per category. Planned Q3 2025.</p>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
            <p className="text-xs font-semibold text-amber-800 mb-1">🔜 Carbon Pricing Simulation</p>
            <p className="text-xs text-amber-700">Model cost of inaction at ₹/tCO₂e. Simulate SBTi pathway scenarios and cost impact on EBITDA. Planned Q3 2025.</p>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
            <p className="text-xs font-semibold text-amber-800 mb-1">🔜 Predictive Reduction Targets</p>
            <p className="text-xs text-amber-700">AI-suggested reduction targets aligned to SBTi 1.5°C pathways based on your emission profile and sector benchmarks. Planned Q4 2025.</p>
          </div>
        </div>
        <div className="mt-3 p-3 bg-gray-50 rounded-xl">
          <p className="text-xs text-gray-500">
            <strong>Model notes:</strong> Spend model R²=0.99 on synthetic training data (expect ±40-60% on real procurement). 
            Forecast PI coverage ~63% (nominal 90%) — treat intervals as indicative. 
            Set <code className="bg-gray-200 px-1 rounded">FORCE_RESEED=false</code> after demo to protect live data.
          </p>
        </div>
      </div>

      {/* Period Modal */}
      <Modal open={periodModal} onClose={() => { setPeriodModal(false); periodForm.reset() }} title="New Reporting Period" size="sm">
        <form onSubmit={periodForm.handleSubmit(onCreatePeriod)} className="space-y-4">
          <div><label className="label">Label *</label><input {...periodForm.register('label', { required: true })} className="input" placeholder="FY2025-26"/></div>
          <div><label className="label">Period Start *</label><input {...periodForm.register('period_start', { required: true })} type="date" className="input"/></div>
          <div><label className="label">Period End *</label><input {...periodForm.register('period_end', { required: true })} type="date" className="input"/></div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => { setPeriodModal(false); periodForm.reset() }} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">{saving ? <Spinner size="sm"/> : 'Create'}</button>
          </div>
        </form>
      </Modal>

      {/* Target Modal */}
      <Modal open={targetModal} onClose={() => { setTargetModal(false); targetForm.reset() }} title="New Emission Target" size="sm">
        <form onSubmit={targetForm.handleSubmit(onCreateTarget)} className="space-y-4">
          <div><label className="label">Label</label><input {...targetForm.register('label')} className="input" placeholder="FY2025 Target"/></div>
          <div><label className="label">Year *</label><input {...targetForm.register('year', { required: true })} type="number" className="input" defaultValue={new Date().getFullYear()}/></div>
          <div><label className="label">Target (tCO₂e) *</label><input {...targetForm.register('target_co2e', { required: true })} type="number" step="any" className="input" placeholder="10000"/></div>
          <div>
            <label className="label">Region</label>
            <select {...targetForm.register('region')} className="input">
              <option value="">All Regions</option>
              {['north','south','east','west','central'].map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase()+r.slice(1)}</option>)}
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => { setTargetModal(false); targetForm.reset() }} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">{saving ? <Spinner size="sm"/> : <><Target size={14}/> Set Target</>}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
