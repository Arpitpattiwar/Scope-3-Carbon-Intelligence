import { useEffect, useState } from 'react'
import { Search, Eye, CheckCircle, XCircle, Download, AlertCircle, ShieldAlert, ShieldCheck, SquareCheck } from 'lucide-react'
import { emissionsApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { PageLoader, QualityBadge, StatusBadge, Modal, SectionHeader, Select, EmptyState } from '@/components/ui'
import { SCOPE3_CATEGORIES, formatCO2e, formatDate } from '@/utils/constants'
import toast from 'react-hot-toast'

const REJECTION_CODES = [
  { value: 'wrong_unit',       label: 'Incorrect unit (e.g. kg instead of tonnes)' },
  { value: 'inflated_value',   label: 'Activity value appears inflated or implausible' },
  { value: 'wrong_ef_applied', label: 'Wrong emission factor selected for this activity' },
  { value: 'missing_docs',     label: 'Supporting documentation required' },
  { value: 'data_quality_low', label: 'Data quality too low — primary data required' },
  { value: 'duplicate_entry',  label: 'Duplicate record for this period' },
  { value: 'period_mismatch',  label: 'Period dates do not match supporting data' },
  { value: 'other',            label: 'Other (describe in notes below)' },
]

export default function EmissionsPage() {
  const { user } = useAuthStore()
  const [records, setRecords]           = useState<any[]>([])
  const [loading, setLoading]           = useState(true)
  const [traceRecord, setTraceRecord]   = useState<any>(null)
  const [traceLoading, setTraceLoading] = useState(false)
  const [rejectModal, setRejectModal]   = useState<{ id: number } | null>(null)
  const [rejectCode, setRejectCode]     = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [search, setSearch]             = useState('')
  const [catFilter, setCatFilter]       = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selected, setSelected]         = useState<Set<number>>(new Set())
  const [bulkModal, setBulkModal]       = useState<'approve' | 'reject' | null>(null)
  const [bulkRejectCode, setBulkRejectCode]   = useState('')
  const [bulkRejectReason, setBulkRejectReason] = useState('')
  const [bulkLoading, setBulkLoading]   = useState(false)

  useEffect(() => { fetchRecords() }, [catFilter, statusFilter])

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (catFilter)    params.category_id = parseInt(catFilter)
      if (statusFilter) params.status      = statusFilter
      const res = await emissionsApi.list(params)
      setRecords(res.data)
      setSelected(new Set())
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
    try {
      await emissionsApi.updateStatus(id, 'approved')
      toast.success('Record approved')
      fetchRecords()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const reject = async () => {
    if (!rejectModal || !rejectCode || !rejectReason.trim()) return
    try {
      await emissionsApi.updateStatus(rejectModal.id, 'rejected', rejectReason, rejectCode)
      toast.success('Record rejected — vendor notified')
      setRejectModal(null); setRejectCode(''); setRejectReason('')
      fetchRecords()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const doBulk = async () => {
    if (selected.size === 0) return
    if (bulkModal === 'reject' && (!bulkRejectCode || !bulkRejectReason.trim())) return
    setBulkLoading(true)
    try {
      const res = await emissionsApi.bulkStatus(
        Array.from(selected),
        bulkModal === 'approve' ? 'approved' : 'rejected',
        bulkRejectReason || undefined,
        bulkRejectCode   || undefined,
      )
      toast.success(res.data.message)
      if (res.data.skipped?.length) {
        toast(`${res.data.skipped.length} records skipped — see console`, { icon: '⚠️' })
        console.table(res.data.skipped)
      }
      setBulkModal(null); setBulkRejectCode(''); setBulkRejectReason('')
      setSelected(new Set())
      fetchRecords()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Bulk action failed') }
    finally { setBulkLoading(false) }
  }

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    const submittedIds = filtered.filter(r => r.status.endsWith('submitted')).map((r: any) => r.id)
    if (selected.size === submittedIds.length) setSelected(new Set())
    else setSelected(new Set(submittedIds))
  }

  const filtered = records.filter(r => {
    if (!search) return true
    const s = search.toLowerCase()
    return String(r.category_id).includes(s) ||
      SCOPE3_CATEGORIES[r.category_id]?.toLowerCase().includes(s) ||
      r.activity_unit?.toLowerCase().includes(s) ||
      r.vendor_company_name?.toLowerCase().includes(s)
  })

  const submittedIds = filtered.filter(r => r.status.endsWith('submitted')).map((r: any) => r.id)
  const allSubmittedSelected = submittedIds.length > 0 && submittedIds.every(id => selected.has(id))
  const showVendorColumn   = user?.role !== 'vendor'
  const canModerate        = ['admin','manager'].includes(user?.role || '')
  const traceAnomaly       = traceRecord?.anomaly_check || traceRecord?.calculation_trace?.anomaly_check

  const catOptions    = [
    { value: '', label: 'All Categories' },
    ...Object.entries(SCOPE3_CATEGORIES).map(([id, name]) => ({ value: id, label: `${id}. ${name}` }))
  ]
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    ...['draft','submitted','approved','rejected'].map(s => ({
      value: s, label: s.charAt(0).toUpperCase()+s.slice(1)
    }))
  ]

  return (
    <div>
      <SectionHeader title="Emission Records" description="All Scope 3 emission data submissions"/>

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by category, vendor, or unit..." className="input pl-9"/>
        </div>
        <Select options={catOptions}    value={catFilter}    onChange={setCatFilter}    className="w-52"/>
        <Select options={statusOptions} value={statusFilter} onChange={setStatusFilter} className="w-36"/>
      </div>

      {/* Bulk action bar */}
      {canModerate && selected.size > 0 && (
        <div className="flex items-center gap-3 mb-4 p-3 bg-indigo-50 border border-indigo-100 rounded-xl">
          <span className="text-sm font-medium text-indigo-700">{selected.size} record{selected.size > 1 ? 's' : ''} selected</span>
          <button onClick={() => setBulkModal('approve')}
            className="btn-primary py-1.5 px-4 text-sm">
            <CheckCircle size={13}/> Approve All
          </button>
          <button onClick={() => setBulkModal('reject')}
            className="btn-danger py-1.5 px-4 text-sm">
            <XCircle size={13}/> Reject All
          </button>
          <button onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-indigo-500 hover:underline">Clear selection</button>
        </div>
      )}

      {loading ? <PageLoader /> : filtered.length === 0 ? (
        <EmptyState title="No records found" description="Emission records submitted by vendors will appear here."/>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {canModerate && (
                    <th className="table-header w-10">
                      <input type="checkbox" checked={allSubmittedSelected}
                        onChange={toggleAll}
                        className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"/>
                    </th>
                  )}
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
                  <tr key={r.id} className={`hover:bg-gray-50 transition-colors ${selected.has(r.id) ? 'bg-indigo-50/40' : ''}`}>
                    {canModerate && (
                      <td className="table-cell">
                        {r.status.endsWith('submitted') && (
                          <input type="checkbox" checked={selected.has(r.id)}
                            onChange={() => toggleSelect(r.id)}
                            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"/>
                        )}
                      </td>
                    )}
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
                        <p className="text-xs text-red-500 mt-0.5 max-w-[140px] truncate"
                           title={r.rejection_reason}>
                          {r.rejection_reason}
                        </p>
                      )}
                    </td>
                    <td className="table-cell text-xs text-gray-500">{formatDate(r.submitted_at)}</td>
                    <td className="table-cell">
                      <div className="flex items-center gap-1">
                        <button onClick={() => openTrace(r.id)}
                          className="p-1.5 hover:bg-brand-50 text-brand-600 rounded-lg transition-colors"
                          title="View calculation trace">
                          <Eye size={14}/>
                        </button>
                        {canModerate && r.status === 'submitted' && (
                          <>
                            <button onClick={() => approve(r.id)}
                              className="p-1.5 hover:bg-green-50 text-green-600 rounded-lg transition-colors"
                              title="Approve">
                              <CheckCircle size={14}/>
                            </button>
                            <button onClick={() => { setRejectModal({ id: r.id }); setRejectCode(''); setRejectReason('') }}
                              className="p-1.5 hover:bg-red-50 text-red-500 rounded-lg transition-colors"
                              title="Reject">
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

      {/* Single Reject modal */}
      <Modal open={!!rejectModal} onClose={() => setRejectModal(null)} title="Reject Record" size="md">
        <div className="space-y-4">
          <div className="p-3 bg-red-50 border border-red-100 rounded-xl flex items-start gap-2">
            <AlertCircle size={16} className="text-red-500 flex-shrink-0 mt-0.5"/>
            <p className="text-sm text-red-700">
              The vendor will be notified by email with the selected reason.
              They can revise and resubmit from their Submission History page.
            </p>
          </div>

          <div>
            <label className="label">Rejection Reason *</label>
            <select value={rejectCode} onChange={e => setRejectCode(e.target.value)} className="input">
              <option value="">Select a reason category</option>
              {REJECTION_CODES.map(c => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Additional Notes *</label>
            <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)}
              className="input" rows={3}
              placeholder="e.g. Your activity value of 8500 tonne is ~10× higher than historical average (850 tonne). Please verify the unit and resubmit."/>
          </div>

          <div className="flex gap-3">
            <button onClick={() => setRejectModal(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={reject}
              disabled={!rejectCode || !rejectReason.trim()}
              className="btn-danger flex-1 justify-center">
              <XCircle size={14}/> Reject Record
            </button>
          </div>
        </div>
      </Modal>

      {/* Bulk action modal */}
      <Modal open={!!bulkModal} onClose={() => setBulkModal(null)}
        title={bulkModal === 'approve' ? `Approve ${selected.size} Records` : `Reject ${selected.size} Records`}
        size="md">
        <div className="space-y-4">
          {bulkModal === 'approve' ? (
            <div className="p-3 bg-green-50 border border-green-100 rounded-xl">
              <p className="text-sm text-green-700">
                All {selected.size} selected records will be approved. Vendors will be notified.
                Records in locked periods or outside your region will be skipped.
              </p>
            </div>
          ) : (
            <>
              <div className="p-3 bg-red-50 border border-red-100 rounded-xl">
                <p className="text-sm text-red-700">
                  All {selected.size} selected records will be rejected. All affected vendors will be notified with the same reason.
                </p>
              </div>
              <div>
                <label className="label">Rejection Reason *</label>
                <select value={bulkRejectCode} onChange={e => setBulkRejectCode(e.target.value)} className="input">
                  <option value="">Select a reason category</option>
                  {REJECTION_CODES.map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Notes *</label>
                <textarea value={bulkRejectReason} onChange={e => setBulkRejectReason(e.target.value)}
                  className="input" rows={2}
                  placeholder="Reason applied to all selected records..."/>
              </div>
            </>
          )}
          <div className="flex gap-3">
            <button onClick={() => setBulkModal(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={doBulk}
              disabled={bulkLoading || (bulkModal === 'reject' && (!bulkRejectCode || !bulkRejectReason.trim()))}
              className={`flex-1 justify-center ${bulkModal === 'approve' ? 'btn-primary' : 'btn-danger'}`}>
              {bulkLoading ? 'Processing…' : bulkModal === 'approve' ? `Approve ${selected.size}` : `Reject ${selected.size}`}
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

            {/* Unit warning */}
            {traceRecord.calculation_trace.unit_warning && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2">
                <AlertCircle size={14} className="text-amber-600 mt-0.5 flex-shrink-0"/>
                <p className="text-xs text-amber-700">{traceRecord.calculation_trace.unit_warning}</p>
              </div>
            )}

            {traceAnomaly && (
              <div className={`p-4 rounded-xl border ${traceAnomaly.is_flagged ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200'}`}>
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${traceAnomaly.is_flagged ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
                    {traceAnomaly.is_flagged ? <ShieldAlert size={16}/> : <ShieldCheck size={16}/>}
                  </div>
                  <div className="flex-1">
                    <p className={`text-sm font-semibold mb-1 ${traceAnomaly.is_flagged ? 'text-amber-800' : 'text-green-800'}`}>
                      {traceAnomaly.is_flagged ? 'Anomaly flag raised' : 'No anomaly detected'}
                    </p>
                    <p className={`text-sm ${traceAnomaly.is_flagged ? 'text-amber-700' : 'text-green-700'}`}>
                      {traceAnomaly.explanation}
                    </p>
                    <div className="grid grid-cols-3 gap-2 mt-3">
                      {[['Anomaly Score', traceAnomaly.anomaly_score],
                        ['Raw Score', traceAnomaly.raw_score ?? '—'],
                        ['Model', traceAnomaly.model_used]].map(([l,v]) => (
                        <div key={l as string} className="p-2 bg-white/70 rounded-lg">
                          <p className="text-[11px] text-gray-500">{l}</p>
                          <p className="text-sm font-mono text-gray-900">{v}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              {([
                ['Activity Value', `${traceRecord.calculation_trace.activity_value} ${traceRecord.calculation_trace.activity_unit}`],
                ['Emission Factor', `${traceRecord.calculation_trace.ef_value} ${traceRecord.calculation_trace.ef_unit}`],
                ['Raw CO₂e', `${traceRecord.calculation_trace.raw_co2e_kg} kgCO₂e`],
                ['Final CO₂e', `${traceRecord.calculation_trace.co2e_tonnes} tCO₂e`],
                ['EF Source', traceRecord.calculation_trace.ef_source],
                ['EF Version', traceRecord.calculation_trace.ef_version],
                ['Data Quality', traceRecord.calculation_trace.data_quality],
                ['Submitted', traceRecord.calculation_trace.submitted_at?.slice(0,19)],
                ['Input Mode', traceRecord.input_mode || 'direct'],
                ['Parent Record', traceRecord.parent_record_id ? `#${traceRecord.parent_record_id}` : '—'],
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

            {traceRecord.parametric_inputs && (
              <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl">
                <p className="text-xs font-semibold text-blue-600 mb-2">Parametric Inputs Used</p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(traceRecord.parametric_inputs).map(([k, v]) => (
                    <div key={k} className="p-2 bg-white/70 rounded-lg">
                      <p className="text-[11px] text-gray-500">{k}</p>
                      <p className="text-sm font-mono text-gray-900">{String(v)}</p>
                    </div>
                  ))}
                </div>
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
