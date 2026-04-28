import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Clock, FileText, TrendingDown, TrendingUp, Download, Star } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { SectionHeader, PageLoader, Select, EmptyState } from '@/components/ui'
import { SCOPE3_CATEGORIES, formatCO2e, downloadBlob } from '@/utils/constants'
import { notificationsApi } from '@/utils/api'
import api from '@/utils/api'
import toast from 'react-hot-toast'

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  approved:  { icon: <CheckCircle2 size={14}/>, color: 'text-green-600 bg-green-50', label: 'Approved' },
  rejected:  { icon: <XCircle size={14}/>, color: 'text-red-500 bg-red-50', label: 'Rejected' },
  submitted: { icon: <Clock size={14}/>, color: 'text-blue-500 bg-blue-50', label: 'Pending' },
  draft:     { icon: <FileText size={14}/>, color: 'text-gray-400 bg-gray-50', label: 'Draft' },
}

const YEARS = Array.from({ length: 5 }, (_, i) => {
  const y = new Date().getFullYear() - i
  return { value: String(y), label: `FY ${y}` }
})

export default function SubmissionHistory() {
  const navigate = useNavigate()
  const [records, setRecords] = useState<any[]>([])
  const [intensity, setIntensity] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [year, setYear] = useState('')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    fetchData()
    fetchIntensity()
  }, [year])

  const fetchData = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (year) params.year = parseInt(year)
      const res = await api.get('/vendor/history', { params })
      setRecords(res.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const fetchIntensity = async () => {
    try {
      const res = await api.get('/vendor/intensity')
      setIntensity(res.data)
    } catch {}
  }

  const exportCsv = async () => {
    setExporting(true)
    try {
      const params: any = {}
      if (year) params.year = parseInt(year)
      const res = await api.get('/vendor/export-csv', { params, responseType: 'blob' })
      downloadBlob(new Blob([res.data], { type: 'text/csv' }), `my_emissions_${year || 'all'}.csv`)
      toast.success('Exported successfully')
    } catch { toast.error('Export failed') }
    finally { setExporting(false) }
  }

  const qualityColor = (q: string) => {
    const val = q.split('.').pop()
    return val === 'A' ? 'badge-A' : val === 'B' ? 'badge-B' : 'badge-C'
  }

  return (
    <div>
      <SectionHeader
        title="Submission History"
        description="Timeline of all your emission records"
        action={
          <div className="flex items-center gap-2">
            <Select options={[{ value: '', label: 'All Years' }, ...YEARS]}
              value={year} onChange={setYear} className="w-28"/>
            <button onClick={exportCsv} disabled={exporting} className="btn-secondary">
              <Download size={14}/> Export CSV
            </button>
          </div>
        }
      />

      {/* Intensity cards */}
      {intensity && intensity.record_count > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="card p-4">
            <p className="text-xs text-gray-500 mb-1">Total CO₂e</p>
            <p className="text-xl font-bold text-brand-700">{formatCO2e(intensity.total_co2e)}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 mb-1">Avg per Record</p>
            <p className="text-xl font-bold text-gray-800">{formatCO2e(intensity.co2e_per_record)}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 mb-1">Data Quality Score</p>
            <p className="text-xl font-bold text-gray-800">{intensity.quality_score_pct}%</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 mb-1">Upgradeable Records</p>
            <p className="text-xl font-bold text-amber-600">{intensity.upgradeable_records?.length ?? 0}</p>
            {intensity.upgradeable_records?.length > 0 && (
              <button onClick={() => navigate('/submit')}
                className="text-xs text-brand-600 hover:underline mt-1">Upgrade now →</button>
            )}
          </div>
        </div>
      )}

      {loading ? <PageLoader /> : records.length === 0 ? (
        <EmptyState title="No records yet"
          description="Submit your first emission record to see your history here."
          action={<button onClick={() => navigate('/submit')} className="btn-primary">Submit Data</button>}/>
      ) : (
        <div className="space-y-3">
          {records.map((r: any) => {
            const sc = STATUS_CONFIG[r.status.split('.').pop()] || STATUS_CONFIG.draft
            return (
              <div key={r.id} className="card p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-gray-50 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-gray-500">C{r.category_id}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold text-gray-900">
                          {SCOPE3_CATEGORIES[r.category_id]}
                        </p>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${sc.color}`}>
                          {sc.icon} {sc.label}
                        </span>
                        <span className={qualityColor(r.data_quality)}>
                          {r.data_quality.split('.').pop()}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {r.period_start} → {r.period_end} · {r.activity_value} {r.activity_unit}
                      </p>
                      {r.rejection_reason && (
                        <p className="text-xs text-red-600 mt-1 bg-red-50 px-2 py-1 rounded-lg">
                          Rejection reason: {r.rejection_reason}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-lg font-bold text-brand-700">{formatCO2e(r.calculated_co2e || 0)}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {r.submitted_at ? new Date(r.submitted_at).toLocaleDateString('en-IN') : '—'}
                    </p>
                    {r.data_quality?.endsWith('C') && r.status !== 'rejected' && (
                      <button onClick={() => navigate('/submit')}
                        className="mt-1 text-xs text-amber-600 hover:underline flex items-center gap-1 justify-end">
                        <Star size={10}/> Upgrade quality
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
