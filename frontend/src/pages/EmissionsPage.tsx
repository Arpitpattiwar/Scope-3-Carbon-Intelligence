import { useEffect, useState } from 'react'
import { Search, Eye, CheckCircle, XCircle, Download, AlertCircle } from 'lucide-react'
import { emissionsApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { PageLoader, QualityBadge, StatusBadge, Modal, SectionHeader, Select, EmptyState } from '@/components/ui'
import { SCOPE3_CATEGORIES, formatCO2e, formatDate } from '@/utils/constants'
import toast from 'react-hot-toast'

export default function EmissionsPage() {
  const { user } = useAuthStore()
  const [records, setRecords] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [traceRecord, setTraceRecord] = useState<any>(null)
  const [traceLoading, setTraceLoading] = useState(false)
  const [rejectModal, setRejectModal] = useState<{ id: number } | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [search, setSearch] = useState('')
  const [catFilter, setCatFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => { fetchRecords() }, [catFilter, statusFilter])

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (catFilter) params.category_id = parseInt(catFilter)
      if (statusFilter) params.status = statusFilter
      const res = await emissionsApi.list(params)
      setRecords(res.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const openTrace = async (id: number) => {
    setTraceLoading(true); setTraceRecord({})
    try { const res = await emissionsApi.getTrace(id); setTraceRecord(res.data) }
    catch { toast.error('Could not load trace') }
    finally { setTraceLoading(false) }
  }

  const approve = async (id: number) => {
    try { await emissionsApi.updateStatus(id, 'approved'); toast.success('Record approved'); fetchRecords() }
    catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const reject = async () => {
    if (!rejectModal || !rejectReason.trim()) return
    try {
      await emissionsApi.updateStatus(rejectModal.id, 'rejected', rejectReason)
      toast.success('Record rejected'); setRejectModal(null); setRejectReason(''); fetchRecords()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const filtered = records.filter(r => {
    if (!search) return true
    const s = search.toLowerCase()
    return String(r.category_id).includes(s) ||
      SCOPE3_CATEGORIES[r.category_id]?.toLowerCase().includes(s) ||
      r.activity_unit?.toLowerCase().includes(s) ||
      r.vendor_company_name?.toLowerCase().includes(s)
  })

  const catOptions = [
    { value: '', label: 'All Categories' },
    ...Object.entries(SCOPE3_CATEGORIES).map(([id, name]) => ({ value: id, label: `${id}. ${name}` }))
  ]
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    ...['draft','submitted','approved','rejected'].map(s => ({ value: s, label: s.charAt(0).toUpperCase()+s.slice(1) }))
  ]

  const showVendorColumn = user?.role !== 'vendor'

  return (
    <div>
      <SectionHeader title="Emission Records" description="All Scope 3 emission data submissions"/>

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by category, vendor, or unit..." className="input pl-9"/>
        </div>
        <Select options={catOptions} value={catFilter} onChange={setCatFilter} className="w-52"/>
        <Select options={statusOptions} value={statusFilter} onChange={setStatusFilter} className="w-36"/>
      </div>

      {loading ? <PageLoader /> : filtered.length === 0 ? (
        <EmptyState title="No records found" description="Emission records submitted by vendors will appear here."/>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {showVendorColumn && <th className="table-header">Vendor</th>}
                  <th className="table-header">Category</th>
                  <th className="table-header">Period</th>
                  <th className="table-header">Activity</th>
                  <th className="table-header">CO₂e</th>
                  <th className="table-header">Quality</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Submitted</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((r: any) => (
                  <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                    {showVendorColumn && (
                      <td className="table-cell">
                        <p className="text-sm font-medium text-gray-800 max-w-[120px] truncate">
                          {r.vendor_company_name || `Vendor #${r.vendor_id}`}
                        </p>
                      </td>
                    )}
                    <td className="table-cell">
                      <p className="font-medium text-gray-900 text-sm">Cat {r.category_id}</p>
                      <p className="text-xs text-gray-400 truncate max-w-[120px]">{SCOPE3_CATEGORIES[r.category_id]}</p>
                    </td>
                    <td className="table-cell text-xs text-gray-500">{r.period_start}<br/>{r.period_end}</td>
                    <td className="table-cell font-mono text-sm">
                      {r.activity_value} <span className="text-gray-400 text-xs">{r.activity_unit}</span>
                    </td>
                    <td className="table-cell font-mono font-semibold text-brand-700">
                      {formatCO2e(r.calculated_co2e || 0)}
                    </td>
                    <td className="table-cell"><QualityBadge quality={r.data_quality}/></td>
                    <td className="table-cell">
                      <StatusBadge status={r.status}/>
                      {r.status === 'rejected' && r.rejection_reason && (
                        <p className="text-xs text-red-500 mt-0.5 max-w-[110px] truncate" title={r.rejection_reason}>
                          {r.rejection_reason}
                        </p>
                      )}
                    </td>
                    <td className="table-cell text-xs text-gray-500">{formatDate(r.submitted_at)}</td>
                    <td className="table-cell">
                      <div className="flex items-center gap-1">
                        <button onClick={() => openTrace(r.id)}
                          className="p-1.5 hover:bg-brand-50 text-brand-600 rounded-lg transition-colors" title="View calculation trace">
                          <Eye size={14}/>
                        </button>
                        {['admin','manager'].includes(user?.role || '') && r.status === 'submitted' && (
                          <>
                            <button onClick={() => approve(r.id)}
                              className="p-1.5 hover:bg-green-50 text-green-600 rounded-lg transition-colors" title="Approve">
                              <CheckCircle size={14}/>
                            </button>
                            <button onClick={() => { setRejectModal({ id: r.id }); setRejectReason('') }}
                              className="p-1.5 hover:bg-red-50 text-red-500 rounded-lg transition-colors" title="Reject">
                              <XCircle size={14}/>
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reject modal */}
      <Modal open={!!rejectModal} onClose={() => setRejectModal(null)} title="Reject Record" size="sm">
        <div className="space-y-4">
          <div className="p-3 bg-red-50 border border-red-100 rounded-xl flex items-start gap-2">
            <AlertCircle size={16} className="text-red-500 flex-shrink-0 mt-0.5"/>
            <p className="text-sm text-red-700">The vendor will be notified by email with this reason. They can correct and resubmit.</p>
          </div>
          <div>
            <label className="label">Rejection Reason *</label>
            <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)}
              className="input" rows={3}
              placeholder="e.g. Incorrect activity unit — should be tonnes not kg. Please resubmit."/>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setRejectModal(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={reject} disabled={!rejectReason.trim()} className="btn-danger flex-1 justify-center">
              <XCircle size={14}/> Reject Record
            </button>
          </div>
        </div>
      </Modal>

      {/* Calculation trace modal */}
      <Modal open={!!traceRecord} onClose={() => setTraceRecord(null)} title="Calculation Trace" size="lg">
        {traceLoading ? (
          <div className="flex items-center justify-center h-40">
            <div className="w-6 h-6 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"/>
          </div>
        ) : traceRecord?.calculation_trace ? (
          <div className="space-y-4">
            <div className="p-4 bg-brand-50 border border-brand-100 rounded-xl">
              <p className="text-xs font-semibold text-brand-700 uppercase tracking-wide mb-2">Formula</p>
              <p className="font-mono text-sm text-brand-900">{traceRecord.calculation_trace.formula}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {([
                ['Activity Value', `${traceRecord.calculation_trace.activity_value} ${traceRecord.calculation_trace.activity_unit}`],
                ['Emission Factor', `${traceRecord.calculation_trace.ef_value} ${traceRecord.calculation_trace.ef_unit}`],
                ['Raw CO₂e', `${traceRecord.calculation_trace.raw_co2e_kg} kgCO₂e`],
                ['Final CO₂e', `${traceRecord.calculation_trace.co2e_tonnes} tCO₂e`],
                ['EF Source', traceRecord.calculation_trace.ef_source],
                ['EF Version', traceRecord.calculation_trace.ef_version],
                ['Data Quality', traceRecord.calculation_trace.data_quality],
                ['Submitted', traceRecord.calculation_trace.submitted_at?.slice(0, 19)],
              ] as [string, string][]).map(([label, value]) => (
                <div key={label} className="p-3 bg-gray-50 rounded-xl">
                  <p className="text-xs text-gray-500 mb-0.5">{label}</p>
                  <p className="text-sm font-medium text-gray-900 font-mono">{value || '—'}</p>
                </div>
              ))}
            </div>
            {traceRecord.calculation_trace.rejection_reason && (
              <div className="p-3 bg-red-50 border border-red-100 rounded-xl">
                <p className="text-xs font-semibold text-red-600 mb-1">Rejection Reason</p>
                <p className="text-sm text-red-700">{traceRecord.calculation_trace.rejection_reason}</p>
              </div>
            )}
            <div className="p-4 bg-gray-50 rounded-xl">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Step-by-step</p>
              <ol className="space-y-1">
                {traceRecord.calculation_trace.steps?.map((s: string, i: number) => (
                  <li key={i} className="text-xs font-mono text-gray-700">{s}</li>
                ))}
              </ol>
            </div>
            {traceRecord.calculation_trace.ef_source_url && (
              <a href={traceRecord.calculation_trace.ef_source_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline">
                <Download size={12}/> View EF source document
              </a>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
