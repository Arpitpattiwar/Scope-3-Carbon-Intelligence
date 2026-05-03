import { useEffect, useState, useCallback, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  AlertCircle, Calculator, ChevronRight, Info, Sparkles,
  Save, Send, Paperclip, X, Upload,
} from 'lucide-react'
import { emissionsApi, efApi, attachmentsApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { PageLoader, Select, QualityBadge, SectionHeader, Modal } from '@/components/ui'
import { SCOPE3_CATEGORIES } from '@/utils/constants'
import toast from 'react-hot-toast'

// ── Constants ──────────────────────────────────────────────────────────────────

const CATEGORY_OPTIONS = Object.entries(SCOPE3_CATEGORIES).map(([id, name]) => ({
  value: id, label: `${id}. ${name}`,
}))
const QUALITY_OPTIONS = [
  { value: 'A', label: 'A — Primary data (invoices, meters, delivery notes)' },
  { value: 'B', label: 'B — Proxy / benchmark / modelled data' },
  { value: 'C', label: 'C — Estimated / spend-based (AI assisted)' },
]
const INPUT_MODE_OPTIONS = [
  { value: 'direct',     label: 'Direct entry — I have the calculated activity value' },
  { value: 'parametric', label: 'Parametric — I have raw measurements (I will guide you)' },
]

const SPEND_ESTIMATE_CATEGORIES = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]

const QUALITY_EXPLAINER: Record<string, { color: string; desc: string; examples: string }> = {
  A: {
    color: 'bg-green-50 border-green-200 text-green-800',
    desc: 'Highest accuracy. Directly measured or metered data.',
    examples: 'Weigh-bridge receipts, fuel meter readings, utility bills, delivery notes with weights',
  },
  B: {
    color: 'bg-blue-50 border-blue-200 text-blue-800',
    desc: 'Good accuracy. Industry averages or proxy data.',
    examples: 'Supplier average intensity, industry benchmark factors, modelled estimates with documented assumptions',
  },
  C: {
    color: 'bg-amber-50 border-amber-200 text-amber-700',
    desc: 'Indicative only. Spend-based or AI-estimated.',
    examples: 'Spend × DEFRA/EEIO factor, AI model estimate. Upgrade to A or B when primary data is available.',
  },
}

const CATEGORY_GUIDANCE: Record<number, string> = {
  1:  'Include all materials, components, and services purchased. Use weight (tonnes) for physical goods or spend (INR) for spend-based. Separate by material type for best accuracy.',
  2:  'Include manufacturing equipment, vehicles, buildings purchased this period. Use weight or lifecycle-based spend.',
  3:  'Include fuel purchased/consumed in operations not covered by Scope 1/2. Use volume (litres) for diesel/petrol.',
  4:  'Include all inbound freight — road, rail, sea, air. Activity = distance (km) × weight (tonnes) = tonne-km.',
  5:  'Include all waste generated at your site. Separate by disposal method (landfill, incineration, recycling) for accurate EF matching.',
  6:  'Include all business trips by air, rail, road. Activity = passenger-km (trips × avg. distance × passengers).',
  7:  'Include daily commute of all employees. Activity = vehicle-km (employees × distance × working days × 2 × (1−WFH%)).',
  8:  'Include all outbound freight to customers. Same formula as Category 4 — distance × weight.',
  9:  'Include energy used in processing your sold products by customers or third-party processors.',
  10: 'Include lifetime energy use of products you sell. Use product energy rating × estimated lifetime.',
  11: 'Include waste generated from products at end-of-life by customers.',
  12: 'Include energy consumed by assets you lease out to others.',
  13: 'Include emissions from your franchise operations. Use revenue-based or activity-based EFs.',
  14: 'Include financed emissions from investment portfolio. Use PCAF methodology.',
  15: 'Use for industry-specific categories not covered above.',
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function SubmitDataPage() {
  const { user } = useAuthStore()
  const location = useLocation()
  const revisingRecord = location.state?.revisingRecord || null

  // Form state
  const [categoryId,    setCategoryId]    = useState(revisingRecord?.category_id?.toString() || '')
  const [inputMode,     setInputMode]     = useState(revisingRecord?.input_mode || 'direct')
  const [periodStart,   setPeriodStart]   = useState(revisingRecord?.period_start || '')
  const [periodEnd,     setPeriodEnd]     = useState(revisingRecord?.period_end || '')
  const [activityValue, setActivityValue] = useState(revisingRecord?.activity_value?.toString() || '')
  const [activityUnit,  setActivityUnit]  = useState(revisingRecord?.activity_unit || '')
  const [efId,          setEfId]          = useState(revisingRecord?.ef_id?.toString() || '')
  const [quality,       setQuality]       = useState<'A'|'B'|'C'>(revisingRecord?.data_quality || 'B')
  const [notes,         setNotes]         = useState(revisingRecord?.notes || '')
  const [isDirty,       setIsDirty]       = useState(false)

  // Parametric state
  const [paramSchema,  setParamSchema]  = useState<any>(null)
  const [paramValues,  setParamValues]  = useState<Record<string,string>>({})
  const [paramResult,  setParamResult]  = useState<any>(null)
  const [paramLoading, setParamLoading] = useState(false)

  // EF state
  const [efs,        setEfs]        = useState<any[]>([])
  const [efsLoading, setEfsLoading] = useState(false)
  const [unitWarning,setUnitWarning] = useState<string | null>(null)

  // AI estimate state
  const [estimateOpen,    setEstimateOpen]    = useState(false)
  const [spendInr,        setSpendInr]        = useState('')
  const [estimateResult,  setEstimateResult]  = useState<any>(null)
  const [estimateLoading, setEstimateLoading] = useState(false)

  // Attachments state
  const [savedRecordId,    setSavedRecordId]    = useState<number | null>(null)
  const [attachments,      setAttachments]      = useState<any[]>([])
  const [attachModal,      setAttachModal]      = useState(false)
  const [attachFile,       setAttachFile]       = useState<File | null>(null)
  const [attachDesc,       setAttachDesc]       = useState('')
  const [attachUploading,  setAttachUploading]  = useState(false)

  // Submission
  const [submitting,  setSubmitting]  = useState(false)

  const catNum = parseInt(categoryId) || 0

  // ── Dirty-state tracking (warn before leaving) ─────────────────────────────
  const navigate = useNavigate()

  // ── Warn on browser close / refresh (works with BrowserRouter) ────────────
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!isDirty) return
      e.preventDefault()
      e.returnValue = ''   // triggers browser's built-in "Leave?" dialog
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  const markDirty = () => setIsDirty(true)

  // ── Load EFs when category changes ────────────────────────────────────────
  const loadEfs = useCallback(async (catId: number) => {
    if (!catId) return
    setEfsLoading(true); setEfs([])
    try {
      // Uses efApi (the /emission-factors endpoint) — NOT a dynamic import
      const res = await efApi.list({ category_id: catId })
      setEfs(res.data)
    } catch (e: any) {
      toast.error('Failed to load emission factors — check backend is running')
      console.error('EF load error:', e)
    } finally { setEfsLoading(false) }
  }, [])

  // ── Load parametric schema ────────────────────────────────────────────────
  const loadParamSchema = useCallback(async (catId: number) => {
    if (!catId) return
    try {
      const res = await emissionsApi.getParametricSchema(catId)
      setParamSchema(res.data.supported ? res.data : null)
    } catch { setParamSchema(null) }
  }, [])

  useEffect(() => {
    if (catNum) {
      loadEfs(catNum)
      loadParamSchema(catNum)
    }
    setParamValues({}); setParamResult(null); setEstimateResult(null)
    setEfId(''); setActivityValue(''); setActivityUnit('')
    setUnitWarning(null)
  }, [catNum])

  // ── Unit mismatch warning ─────────────────────────────────────────────────
  useEffect(() => {
    if (!efId || !activityUnit || !efs.length) { setUnitWarning(null); return }
    const ef = efs.find(e => e.id === parseInt(efId))
    if (!ef) { setUnitWarning(null); return }
    const efDenom = ef.unit?.toLowerCase().split('/').slice(1).join('/') || ''
    const actUnit = activityUnit.toLowerCase()
      .replace(/s$/, '').replace('litres','litre').replace('tonnes','tonne')
    const mismatched = efDenom && actUnit && !efDenom.includes(actUnit) && !actUnit.includes(efDenom)
    setUnitWarning(mismatched
      ? `Unit mismatch: you entered '${activityUnit}' but this EF is per '${efDenom}'. Please verify or convert your activity value.`
      : null)
  }, [efId, activityUnit, efs])

  // ── Parametric auto-calculate ─────────────────────────────────────────────
  const calculateParametric = useCallback(async () => {
    if (!catNum || !paramSchema) return
    const required = paramSchema.fields?.filter((f: any) => f.type !== 'select') || []
    const allFilled = required.every((f: any) => paramValues[f.key]?.trim())
    if (!allFilled) return
    setParamLoading(true)
    try {
      const numParams: Record<string,any> = {}
      for (const [k,v] of Object.entries(paramValues)) {
        numParams[k] = isNaN(Number(v)) ? v : Number(v)
      }
      const res = await emissionsApi.calculateParametric(catNum, numParams)
      setParamResult(res.data)
      setActivityValue(String(res.data.activity_value))
      setActivityUnit(res.data.activity_unit)
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Calculation failed')
    } finally { setParamLoading(false) }
  }, [catNum, paramSchema, paramValues])

  useEffect(() => {
    if (inputMode === 'parametric') calculateParametric()
  }, [paramValues])

  // ── AI spend estimate ─────────────────────────────────────────────────────
  const runEstimate = async () => {
    if (!spendInr || !catNum) return
    setEstimateLoading(true)
    try {
      const res = await emissionsApi.estimateMissing({
        category_id: catNum, spend_inr: parseFloat(spendInr),
      })
      setEstimateResult(res.data)
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Estimation failed')
    } finally { setEstimateLoading(false) }
  }

  const acceptEstimate = async () => {
    if (!estimateResult || !catNum || !periodStart || !periodEnd) {
      toast.error('Fill the reporting period before accepting estimate'); return
    }
    try {
      const res = await emissionsApi.acceptEstimate({
        category_id: catNum, period_start: periodStart, period_end: periodEnd,
        spend_inr: parseFloat(spendInr),
      })
      setSavedRecordId(res.data.id)
      toast.success('AI estimate saved as draft — review in My History')
      setEstimateOpen(false); setIsDirty(false)
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  // ── Attachments ───────────────────────────────────────────────────────────
  const loadAttachments = async (recordId: number) => {
    try {
      const res = await attachmentsApi.list(recordId)
      setAttachments(res.data)
    } catch { /* non-critical */ }
  }

  const uploadAttachment = async () => {
    if (!attachFile || !savedRecordId) return
    setAttachUploading(true)
    try {
      await attachmentsApi.upload(savedRecordId, attachFile, attachDesc)
      toast.success('Attachment uploaded')
      setAttachFile(null); setAttachDesc('')
      loadAttachments(savedRecordId)
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Upload failed') }
    finally { setAttachUploading(false) }
  }

  const deleteAttachment = async (id: number) => {
    try {
      await attachmentsApi.delete(id)
      setAttachments(prev => prev.filter(a => a.id !== id))
    } catch { toast.error('Delete failed') }
  }

  // ── Build submit payload ──────────────────────────────────────────────────
  const buildPayload = () => ({
    category_id:       catNum,
    period_start:      periodStart,
    period_end:        periodEnd,
    activity_value:    parseFloat(activityValue),
    activity_unit:     activityUnit,
    ef_id:             parseInt(efId),
    data_quality:      quality,
    input_method:      'manual',
    input_mode:        inputMode,
    parametric_inputs: inputMode === 'parametric' ? paramValues : undefined,
    notes:             notes || undefined,
    parent_record_id:  revisingRecord?.id || undefined,
  })

  const validate = () => {
    if (!categoryId) { toast.error('Select a Scope 3 category'); return false }
    if (!periodStart || !periodEnd) { toast.error('Set the reporting period'); return false }
    if (!activityValue || isNaN(parseFloat(activityValue))) {
      toast.error('Enter a valid activity value'); return false
    }
    if (!activityUnit) { toast.error('Enter the activity unit'); return false }
    if (!efId) { toast.error('Select an emission factor'); return false }
    return true
  }

  const handleSubmit = async (asDraft: boolean) => {
    if (!validate()) return
    setSubmitting(true)
    try {
      const res = asDraft
        ? await emissionsApi.saveDraft(buildPayload())
        : await emissionsApi.create(buildPayload())
      setSavedRecordId(res.data.id)
      setIsDirty(false)
      if (asDraft) {
        toast.success('Saved as draft — submit from My History when ready')
      } else {
        toast.success(revisingRecord
          ? 'Revised record submitted — manager notified to re-review'
          : 'Record submitted for manager review')
        // Reset form if not revising
        if (!revisingRecord) {
          setCategoryId(''); setPeriodStart(''); setPeriodEnd('')
          setActivityValue(''); setActivityUnit(''); setEfId('')
          setQuality('B'); setNotes('')
          setParamValues({}); setParamResult(null)
        }
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Submission failed')
    } finally { setSubmitting(false) }
  }

  const selectedEf = efs.find(e => e.id === parseInt(efId))
  const qualityInfo = QUALITY_EXPLAINER[quality]

  return (
    <div className="max-w-3xl mx-auto">
      <SectionHeader
        title={revisingRecord ? 'Revise & Resubmit Record' : 'Submit Emission Data'}
        description={revisingRecord
          ? `Correcting record #${revisingRecord.id}. A new linked record will be created.`
          : 'Submit your Scope 3 activity data for manager review.'}
      />

      {/* Revision banner */}
      {revisingRecord && (
        <div className="mb-5 p-4 bg-orange-50 border border-orange-200 rounded-xl">
          <div className="flex items-start gap-3">
            <AlertCircle size={16} className="text-orange-500 flex-shrink-0 mt-0.5"/>
            <div>
              <p className="text-sm font-semibold text-orange-800 mb-1">
                Revising rejected record #{revisingRecord.id}
              </p>
              {revisingRecord.rejection_reason && (
                <p className="text-sm text-orange-700">
                  <strong>Rejection reason:</strong> {revisingRecord.rejection_reason}
                </p>
              )}
              <p className="text-xs text-orange-500 mt-1">
                Fix the issue and submit. The new record links to the original for audit continuity.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="card p-6 space-y-6">

        {/* Category + mode */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Scope 3 Category *</label>
            <Select
              options={[{ value: '', label: 'Select category…' }, ...CATEGORY_OPTIONS]}
              value={categoryId}
              onChange={v => { setCategoryId(v); markDirty() }}
            />
          </div>
          <div>
            <label className="label">Data Entry Mode</label>
            <Select
              options={INPUT_MODE_OPTIONS}
              value={inputMode}
              onChange={v => {
                setInputMode(v)
                setParamValues({}); setParamResult(null)
                setActivityValue(''); setActivityUnit('')
                markDirty()
              }}
            />
          </div>
        </div>

        {/* Category guidance */}
        {catNum > 0 && CATEGORY_GUIDANCE[catNum] && (
          <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-100 rounded-xl">
            <Info size={13} className="text-blue-500 flex-shrink-0 mt-0.5"/>
            <p className="text-xs text-blue-700 leading-relaxed">{CATEGORY_GUIDANCE[catNum]}</p>
          </div>
        )}

        {/* Reporting period */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Period Start *</label>
            <input type="date" value={periodStart}
              onChange={e => { setPeriodStart(e.target.value); markDirty() }} className="input"/>
          </div>
          <div>
            <label className="label">Period End *</label>
            <input type="date" value={periodEnd}
              onChange={e => { setPeriodEnd(e.target.value); markDirty() }} className="input"/>
          </div>
        </div>

        {/* ── PARAMETRIC MODE ─────────────────────────────────────────────── */}
        {inputMode === 'parametric' && catNum > 0 && (
          <div className="p-4 bg-teal-50 border border-teal-100 rounded-xl space-y-4">
            <div className="flex items-center gap-2">
              <Calculator size={14} className="text-teal-600"/>
              <p className="text-sm font-semibold text-teal-800">Parametric Entry</p>
              {paramSchema && (
                <span className="ml-auto text-xs text-teal-600 font-mono bg-teal-100 px-2 py-0.5 rounded">
                  {paramSchema.formula}
                </span>
              )}
            </div>
            {!paramSchema ? (
              <p className="text-sm text-gray-500 bg-white/60 p-3 rounded-lg">
                Parametric entry is not configured for Category {catNum}.
                Switch to <strong>Direct entry</strong> and enter your calculated activity value.
              </p>
            ) : (
              <>
                {paramSchema.note && (
                  <p className="text-xs text-teal-700 bg-teal-100/60 p-2 rounded-lg">{paramSchema.note}</p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {paramSchema.fields?.map((field: any) => (
                    <div key={field.key}>
                      <label className="label">
                        {field.label}
                        {field.help && (
                          <span className="ml-1 text-gray-400 font-normal text-xs normal-case">
                            {' '}— {field.help}
                          </span>
                        )}
                      </label>
                      {field.type === 'select' ? (
                        <Select
                          options={(field.options || []).map((o: string) => ({ value: o, label: o }))}
                          value={paramValues[field.key] || field.options?.[0] || ''}
                          onChange={v => setParamValues(p => ({ ...p, [field.key]: v }))}
                        />
                      ) : (
                        <input type="number" min="0"
                          value={paramValues[field.key] || ''}
                          onChange={e => setParamValues(p => ({ ...p, [field.key]: e.target.value }))}
                          placeholder={field.placeholder || ''}
                          className="input"/>
                      )}
                    </div>
                  ))}
                </div>
                {paramLoading && (
                  <p className="text-sm text-teal-600 flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-teal-500 border-t-transparent rounded-full animate-spin inline-block"/>
                    Calculating…
                  </p>
                )}
                {paramResult && (
                  <div className="p-3 bg-white border border-teal-200 rounded-xl">
                    <p className="text-xs font-semibold text-teal-700 mb-1.5 flex items-center gap-1">
                      <Calculator size={11}/> Calculated Activity Value
                    </p>
                    <p className="text-xl font-bold text-teal-900 font-mono mb-1">
                      {paramResult.activity_value}{' '}
                      <span className="text-sm font-medium text-teal-600">{paramResult.activity_unit}</span>
                    </p>
                    {paramResult.steps?.map((s: string, i: number) => (
                      <p key={i} className="text-xs font-mono text-gray-500">→ {s}</p>
                    ))}
                    <p className="text-xs text-gray-400 mt-2">
                      This value is pre-filled below. Select the matching emission factor.
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── DIRECT MODE ─────────────────────────────────────────────────── */}
        {inputMode === 'direct' && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Activity Value *</label>
              <input type="number" min="0" value={activityValue}
                onChange={e => { setActivityValue(e.target.value); markDirty() }}
                placeholder="e.g. 500" className="input"/>
            </div>
            <div>
              <label className="label">Unit *</label>
              <input type="text" value={activityUnit}
                onChange={e => { setActivityUnit(e.target.value); markDirty() }}
                placeholder="e.g. tonne, litre, tonne-km, passenger-km"
                className="input"/>
              <p className="text-xs text-gray-400 mt-1">Must match the EF unit denominator selected below</p>
            </div>
          </div>
        )}

        {/* Unit warning */}
        {unitWarning && (
          <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl">
            <AlertCircle size={13} className="text-amber-600 flex-shrink-0 mt-0.5"/>
            <p className="text-xs text-amber-700">{unitWarning}</p>
          </div>
        )}

        {/* Emission Factor */}
        <div>
          <label className="label">Emission Factor *</label>
          {efsLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
              <span className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"/>
              Loading factors for Category {catNum}…
            </div>
          ) : efs.length === 0 ? (
            <p className="text-sm text-gray-400 py-2">
              {catNum ? 'No emission factors found for this category. Ask your admin to add factors.' : 'Select a category first.'}
            </p>
          ) : (
            <select value={efId}
              onChange={e => { setEfId(e.target.value); markDirty() }}
              className="input">
              <option value="">Select emission factor…</option>
              {efs.map((ef: any) => (
                <option key={ef.id} value={ef.id}>
                  {ef.material_type || ef.subcategory} — {ef.factor_value} {ef.unit} ({ef.source} {ef.version_tag})
                </option>
              ))}
            </select>
          )}
          {selectedEf && (
            <div className="mt-2 p-3 bg-gray-50 border border-gray-100 rounded-xl">
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-2">
                {([
                  ['Factor value', `${selectedEf.factor_value} ${selectedEf.unit}`],
                  ['Source', `${selectedEf.source} ${selectedEf.version_tag}`],
                  ['Region', selectedEf.region || 'global'],
                  ['Valid from', selectedEf.valid_from || '—'],
                ] as [string,string][]).map(([l,v]) => (
                  <div key={l} className="flex gap-2">
                    <span className="text-xs text-gray-400 w-20 flex-shrink-0">{l}</span>
                    <span className="text-xs text-gray-700 font-mono">{v}</span>
                  </div>
                ))}
              </div>
              {selectedEf.notes && (
                <p className="text-xs text-gray-500 italic">{selectedEf.notes}</p>
              )}
              {selectedEf.source_url && (
                <a href={selectedEf.source_url} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-brand-600 hover:underline mt-1 inline-block">
                  View source document →
                </a>
              )}
            </div>
          )}
        </div>

        {/* Data Quality */}
        <div>
          <label className="label">Data Quality</label>
          <Select
            options={QUALITY_OPTIONS}
            value={quality}
            onChange={v => { setQuality(v as 'A'|'B'|'C'); markDirty() }}
          />
          {qualityInfo && (
            <div className={`mt-2 p-3 border rounded-xl text-xs ${qualityInfo.color}`}>
              <p className="font-semibold mb-0.5">{qualityInfo.desc}</p>
              <p className="opacity-80">Examples: {qualityInfo.examples}</p>
            </div>
          )}
        </div>

        {/* Notes */}
        <div>
          <label className="label">Notes / Assumptions</label>
          <textarea value={notes}
            onChange={e => { setNotes(e.target.value); markDirty() }}
            className="input" rows={2}
            placeholder="Add context, assumptions, source references, or data gaps…"/>
        </div>

        {/* ── AI Spend Estimate ────────────────────────────────────────────── */}
        {catNum > 0 && SPEND_ESTIMATE_CATEGORIES.includes(catNum) && (
          <div className="border border-dashed border-purple-200 rounded-xl overflow-hidden">
            <button type="button" onClick={() => setEstimateOpen(o => !o)}
              className="w-full flex items-center gap-2 p-3 text-left hover:bg-purple-50/50 transition-colors">
              <Sparkles size={14} className="text-purple-500"/>
              <span className="text-sm font-medium text-purple-700">
                No activity data? Use AI spend-based estimate
              </span>
              <ChevronRight size={14}
                className={`ml-auto text-purple-400 transition-transform ${estimateOpen ? 'rotate-90' : ''}`}/>
            </button>
            {estimateOpen && (
              <div className="p-4 border-t border-purple-100 space-y-4 bg-purple-50/30">
                <p className="text-xs text-gray-500">
                  Enter total spend for this category and get an AI estimate.
                  {(catNum <= 2 || catNum >= 13)
                    ? ' Uses XGBoost ML model (DEFRA/EEIO).'
                    : ' Uses DEFRA rule-based spend intensity factors.'}
                  {' '}Result saved as Data Quality C draft.
                </p>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label className="label">Total Spend (INR) *</label>
                    <input type="number" value={spendInr}
                      onChange={e => setSpendInr(e.target.value)}
                      placeholder="e.g. 5000000" className="input"/>
                  </div>
                  <div className="flex items-end">
                    <button onClick={runEstimate}
                      disabled={!spendInr || estimateLoading || !periodStart}
                      className="btn-secondary whitespace-nowrap">
                      {estimateLoading ? 'Estimating…' : 'Get Estimate'}
                    </button>
                  </div>
                </div>
                {estimateResult && (
                  <div className="p-4 bg-white border border-purple-100 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-base font-bold text-purple-900">
                        {estimateResult.estimated_co2e.toFixed(4)} tCO₂e
                      </p>
                      <QualityBadge quality={estimateResult.data_quality}/>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2 bg-purple-50 rounded-lg">
                        <p className="text-gray-400 mb-0.5">90% Band</p>
                        <p className="font-mono">[{estimateResult.confidence_band?.[0]} – {estimateResult.confidence_band?.[1]}]</p>
                      </div>
                      <div className="p-2 bg-purple-50 rounded-lg">
                        <p className="text-gray-400 mb-0.5">Model</p>
                        <p className="font-mono">{estimateResult.model_used}</p>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">{estimateResult.explanation}</p>
                    <p className="text-xs text-gray-400 italic">{estimateResult.methodology_reference}</p>
                    <div className="flex gap-2">
                      <button onClick={acceptEstimate} className="btn-primary text-sm py-1.5">
                        <Save size={13}/> Accept & Save as Draft
                      </button>
                      <button onClick={() => setEstimateResult(null)} className="btn-secondary text-sm py-1.5">
                        Discard
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Submit buttons */}
        <div className="flex gap-3 pt-2 border-t border-gray-100">
          <button type="button" onClick={() => handleSubmit(true)}
            disabled={submitting || !categoryId || !efId || !activityValue}
            className="btn-secondary flex-1 justify-center gap-1.5">
            <Save size={14}/> Save Draft
          </button>
          <button type="button" onClick={() => handleSubmit(false)}
            disabled={submitting || !categoryId || !activityValue || !efId}
            className="btn-primary flex-1 justify-center gap-1.5">
            <Send size={14}/>
            {submitting ? 'Submitting…'
              : revisingRecord ? 'Resubmit for Review'
              : 'Submit for Review'}
          </button>
        </div>

        {/* Attachments — shown after draft/submit */}
        {savedRecordId && (
          <div className="border-t border-gray-100 pt-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                <Paperclip size={14}/> Supporting Documents
              </p>
              <button onClick={() => { setAttachModal(true); loadAttachments(savedRecordId) }}
                className="btn-secondary text-xs py-1 px-3">
                <Upload size={12}/> Attach File
              </button>
            </div>
            {attachments.length === 0 ? (
              <p className="text-xs text-gray-400">
                No attachments yet. Attach invoices, delivery notes, or meter readings to support this record.
              </p>
            ) : (
              <div className="space-y-2">
                {attachments.map((a: any) => (
                  <div key={a.id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg text-sm">
                    <span className="truncate max-w-xs">{a.filename || a.file_name}</span>
                    <button onClick={() => deleteAttachment(a.id)} className="text-red-400 hover:text-red-600 ml-2">
                      <X size={14}/>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Attachment upload modal */}
      <Modal open={attachModal} onClose={() => setAttachModal(false)} title="Attach Supporting Document" size="sm">
        <div className="space-y-4">
          <div>
            <label className="label">File *</label>
            <input type="file" onChange={e => setAttachFile(e.target.files?.[0] || null)}
              className="input text-sm" accept=".pdf,.xlsx,.xls,.csv,.jpg,.png,.docx"/>
          </div>
          <div>
            <label className="label">Description</label>
            <input type="text" value={attachDesc} onChange={e => setAttachDesc(e.target.value)}
              placeholder="e.g. Invoice #INV-2024-001, Delivery note" className="input"/>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setAttachModal(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={uploadAttachment} disabled={!attachFile || attachUploading}
              className="btn-primary flex-1 justify-center">
              {attachUploading ? 'Uploading…' : 'Upload'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
