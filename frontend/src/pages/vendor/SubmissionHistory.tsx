import { useEffect, useState } from 'react'
import { RefreshCw, Eye, AlertCircle, ChevronRight, FileWarning } from 'lucide-react'
import { emissionsApi } from '@/utils/api'
import { PageLoader, StatusBadge, QualityBadge, Modal, EmptyState, SectionHeader } from '@/components/ui'
import { SCOPE3_CATEGORIES, formatCO2e, formatDate } from '@/utils/constants'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

const TABS = [
  { key: '',          label: 'All' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'approved',  label: 'Approved' },
  { key: 'rejected',  label: 'Action Required' },
  { key: 'draft',     label: 'Drafts' },
]

export default function SubmissionHistory() {
  const navigate = useNavigate()
  const [records, setRecords]         = useState<any[]>([])
  const [loading, setLoading]         = useState(true)
  const [activeTab, setActiveTab]     = useState('')
  const [traceRecord, setTraceRecord] = useState<any>(null)
  const [traceLoading, setTraceLoading] = useState(false)

  useEffect(() => { fetchRecords() }, [activeTab])

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (activeTab) params.status = activeTab
      const res = await emissionsApi.list(params)
      setRecords(res.data)
    } catch { toast.error('Failed to load records') }
    finally { setLoading(false) }
  }

  const openTrace = async (id: number) => {
    setTraceLoading(true); setTraceRecord({})
    try { const res = await emissionsApi.getTrace(id); setTraceRecord(res.data) }
    catch { toast.error('Could not load trace') }
    finally { setTraceLoading(false) }
  }

  const submitDraft = async (id: number) => {
    try {
      await emissionsApi.submitDraft(id)
      toast.success('Record submitted for review')
      fetchRecords()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const reviseRecord = (record: any) => {
    // Navigate to submit page with pre-filled state from the rejected record
    navigate('/submit', { state: { revisingRecord: record } })
  }

  const rejectedCount = records.filter(r => r.status === 'rejected').length
  const draftCount    = records.filter(r => r.status === 'draft').length

  return (
    <div>
      <SectionHeader
        title="Submission History"
        description="Track all your submitted, approved, and rejected emission records."
      />

      {/* Alert banner for rejected + drafts */}
      {(rejectedCount > 0 || draftCount > 0) && (
        <div className="mb-4 space-y-2">
          {rejectedCount > 0 && (
            <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-100 rounded-xl">
              <FileWarning size={16} className="text-red-500 flex-shrink-0"/>
              <p className="text-sm text-red-700">
                <span className="font-semibold">{rejectedCount} record{rejectedCount > 1 ? 's' : ''} rejected</span>
                {' '}— click <strong>Revise & Resubmit</strong> to correct and resend.
              </p>
              <button onClick={() => setActiveTab('rejected')}
                className="ml-auto text-xs text-red-600 font-medium hover:underline whitespace-nowrap">
                View all <ChevronRight size={12} className="inline"/>
              </button>
            </div>
          )}
          {draftCount > 0 && (
            <div className="flex items-center gap-3 p-3 bg-amber-50 border border-amber-100 rounded-xl">
              <AlertCircle size={16} className="text-amber-500 flex-shrink-0"/>
              <p className="text-sm text-amber-700">
                <span className="font-semibold">{draftCount} draft{draftCount > 1 ? 's' : ''} saved</span>
                {' '}— submit when ready for manager review.
              </p>
              <button onClick={() => setActiveTab('draft')}
                className="ml-auto text-xs text-amber-600 font-medium hover:underline whitespace-nowrap">
                View drafts <ChevronRight size={12} className="inline"/>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-5 p-1 bg-gray-100 rounded-xl w-fit">
        {TABS.map(t => (
          <button key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === t.key
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}>
            {t.label}
            {t.key === 'rejected' && rejectedCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-red-100 text-red-600 rounded-full">
                {rejectedCount}
              </span>
            )}
            {t.key === 'draft' && draftCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-amber-100 text-amber-600 rounded-full">
                {draftCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? <PageLoader /> : records.length === 0 ? (
        <EmptyState
          title={activeTab === 'rejected' ? 'No rejected records' : activeTab === 'draft' ? 'No drafts saved' : 'No records yet'}
          description={activeTab === 'rejected'
            ? 'All your submissions are in good standing.'
            : activeTab === 'draft'
            ? 'Start a new submission and click "Save Draft" to store it here.'
            : 'Submit your first emission record to see it here.'}
        />
      ) : (
        <div className="space-y-3">
          {records.map((r: any) => (
            <div key={r.id}
              className={`card p-4 transition-colors ${
                r.status === 'rejected' ? 'border-l-4 border-l-red-400' :
                r.status === 'approved' ? 'border-l-4 border-l-green-400' :
                r.status === 'draft'    ? 'border-l-4 border-l-amber-400' : ''
              }`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className="text-xs font-semibold text-gray-500 uppercase">
                      Cat {r.category_id}
                    </span>
                    <span className="text-sm font-semibold text-gray-900">
                      {SCOPE3_CATEGORIES[r.category_id]}
                    </span>
                    <StatusBadge status={r.status}/>
                    <QualityBadge quality={r.data_quality}/>
                    {r.is_ai_estimated && (
                      <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                        AI Estimate
                      </span>
                    )}
                    {r.parent_record_id && (
                      <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                        Revised record
                      </span>
                    )}
                    {r.input_mode === 'parametric' && (
                      <span className="px-2 py-0.5 text-xs bg-teal-100 text-teal-700 rounded-full">
                        Parametric entry
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-1 text-sm">
                    <div>
                      <span className="text-gray-400 text-xs">Period</span>
                      <p className="text-gray-700">{r.period_start} → {r.period_end}</p>
                    </div>
                    <div>
                      <span className="text-gray-400 text-xs">Activity</span>
                      <p className="text-gray-700 font-mono">
                        {r.activity_value} <span className="text-gray-400">{r.activity_unit}</span>
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-400 text-xs">CO₂e</span>
                      <p className="text-brand-700 font-semibold font-mono">{formatCO2e(r.calculated_co2e || 0)}</p>
                    </div>
                    <div>
                      <span className="text-gray-400 text-xs">Submitted</span>
                      <p className="text-gray-700">{formatDate(r.submitted_at)}</p>
                    </div>
                  </div>

                  {/* Rejection reason — prominent display */}
                  {r.status === 'rejected' && r.rejection_reason && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-xl">
                      <div className="flex items-start gap-2">
                        <AlertCircle size={14} className="text-red-500 flex-shrink-0 mt-0.5"/>
                        <div>
                          <p className="text-xs font-semibold text-red-700 mb-0.5">Rejection Reason</p>
                          <p className="text-sm text-red-700">{r.rejection_reason}</p>
                          <p className="text-xs text-red-500 mt-1">
                            Click <strong>Revise & Resubmit</strong> below to correct and send a new version.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {r.notes && r.status !== 'rejected' && (
                    <p className="text-xs text-gray-400 mt-2">Notes: {r.notes}</p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2 flex-shrink-0">
                  <button onClick={() => openTrace(r.id)}
                    className="btn-secondary py-1.5 px-3 text-xs">
                    <Eye size={12}/> Trace
                  </button>
                  {r.status === 'draft' && (
                    <button onClick={() => submitDraft(r.id)}
                      className="btn-primary py-1.5 px-3 text-xs">
                      Submit
                    </button>
                  )}
                  {r.status === 'rejected' && (
                    <button onClick={() => reviseRecord(r)}
                      className="btn-primary py-1.5 px-3 text-xs bg-orange-500 hover:bg-orange-600 border-orange-500">
                      <RefreshCw size={12}/> Revise & Resubmit
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Trace modal */}
      <Modal open={!!traceRecord} onClose={() => setTraceRecord(null)} title="Calculation Trace" size="lg">
        {traceLoading ? (
          <div className="flex items-center justify-center h-40">
            <div className="w-6 h-6 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"/>
          </div>
        ) : traceRecord?.calculation_trace ? (
          <div className="space-y-4">
            {traceRecord.calculation_trace.unit_warning && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2">
                <AlertCircle size={14} className="text-amber-600 mt-0.5"/>
                <p className="text-xs text-amber-700">{traceRecord.calculation_trace.unit_warning}</p>
              </div>
            )}
            <div className="p-4 bg-brand-50 border border-brand-100 rounded-xl">
              <p className="text-xs font-semibold text-brand-700 uppercase tracking-wide mb-1">Formula</p>
              <p className="font-mono text-sm text-brand-900">{traceRecord.calculation_trace.formula}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {([
                ['Activity', `${traceRecord.calculation_trace.activity_value} ${traceRecord.calculation_trace.activity_unit}`],
                ['Normalised', traceRecord.calculation_trace.normalised_value !== traceRecord.calculation_trace.activity_value
                  ? `${traceRecord.calculation_trace.normalised_value} ${traceRecord.calculation_trace.normalised_unit}` : '—'],
                ['Emission Factor', `${traceRecord.calculation_trace.ef_value} ${traceRecord.calculation_trace.ef_unit}`],
                ['EF Source', traceRecord.calculation_trace.ef_source],
                ['EF Version', traceRecord.calculation_trace.ef_version],
                ['Raw CO₂e', `${traceRecord.calculation_trace.raw_co2e_kg} kgCO₂e`],
                ['Final CO₂e', `${traceRecord.calculation_trace.co2e_tonnes} tCO₂e`],
                ['Input Mode', traceRecord.input_mode || 'direct'],
              ] as [string,string][]).map(([l,v]) => (
                <div key={l} className="p-3 bg-gray-50 rounded-xl">
                  <p className="text-xs text-gray-400">{l}</p>
                  <p className="text-sm font-mono text-gray-900 mt-0.5">{v || '—'}</p>
                </div>
              ))}
            </div>
            {traceRecord.parametric_inputs && (
              <div className="p-3 bg-teal-50 border border-teal-100 rounded-xl">
                <p className="text-xs font-semibold text-teal-700 mb-2">Parametric Inputs</p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(traceRecord.parametric_inputs).map(([k,v]) => (
                    <div key={k} className="p-2 bg-white/70 rounded-lg">
                      <p className="text-[11px] text-gray-400">{k}</p>
                      <p className="text-sm font-mono">{String(v)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="p-4 bg-gray-50 rounded-xl">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Steps</p>
              <ol className="space-y-1">
                {traceRecord.calculation_trace.steps?.map((s: string, i: number) => (
                  <li key={i} className="text-xs font-mono text-gray-700">{s}</li>
                ))}
              </ol>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
