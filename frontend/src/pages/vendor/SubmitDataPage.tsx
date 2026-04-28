import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Upload, FileText, CheckCircle2, AlertTriangle, HelpCircle, Calculator } from 'lucide-react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { emissionsApi, efApi, reportsApi, profileApi } from '@/utils/api'
import { Spinner, SectionHeader, QualityBadge } from '@/components/ui'
import { SCOPE3_CATEGORIES, formatCO2e, downloadBlob } from '@/utils/constants'
import HelpTooltip from '@/components/ui/HelpTooltip'

const UNIT_BY_CATEGORY: Record<number, string[]> = {
  1:  ['tonnes','kg','INR (spend-based)','litres','kL (kilolitres)'],
  2:  ['tonnes','units','INR (spend-based)','kg'],
  3:  ['kWh','MWh','litres','kg'],
  4:  ['tonne-km','km','litres','kL (kilolitres)'],
  5:  ['tonnes','kg'],
  6:  ['passenger-km','vehicle-km','nights','km'],
  7:  ['passenger-km','vehicle-km','km'],
  8:  ['tonne-km','km','litres'],
  9:  ['kWh','MWh','tonnes'],
  10: ['units','kWh','MWh'],
  11: ['tonnes','kg'],
  12: ['kWh','MWh'],
  13: ['INR (spend-based)','units'],
  14: ['INR (invested)'],
  15: ['units','kg','tonnes','kWh','INR'],
}

// Full unit list shown when no category is selected (same as onboarding)
const ALL_UNITS = [
  'tonnes', 'kg', 'litres', 'kL (kilolitres)', 'kWh', 'MWh',
  'km', 'tonne-km', 'passenger-km', 'vehicle-km',
  'units', 'pieces', 'INR (spend-based)', 'INR (invested)', 'USD (spend-based)',
  'nights',
]

export default function SubmitDataPage() {
  const [tab, setTab] = useState<'manual' | 'csv'>('manual')
  const [efs, setEfs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [csvResult, setCsvResult] = useState<any>(null)
  const [preview, setPreview] = useState<any>(null)
  const [vendorCategory, setVendorCategory] = useState<number | null>(null)
  const [unitOptions, setUnitOptions] = useState<string[]>([])

  const { register, handleSubmit, watch, reset, setValue, formState: { errors } } = useForm()

  const watchCat      = watch('category_id')
  const watchActivity = watch('activity_value')
  const watchEf       = watch('ef_id')
  const watchStart    = watch('period_start')
  const watchUnit     = watch('activity_unit')

  // Load vendor's own category to prepopulate
  useEffect(() => {
    profileApi.getVendorDetails().then(r => {
      if (r.data?.material_category) {
        setVendorCategory(r.data.material_category)
        setValue('category_id', String(r.data.material_category))
      }
    }).catch(() => {})
  }, [])

  // Load EFs when category changes
  useEffect(() => {
    if (watchCat) {
      const catNum = parseInt(watchCat)
      efApi.list({ category_id: catNum }).then(r => setEfs(r.data))
      setUnitOptions(UNIT_BY_CATEGORY[catNum] || ['kg','tonnes','kWh','km','INR'])
      setValue('ef_id', '')
      setPreview(null)
    }
  }, [watchCat])

  // Live CO₂e preview
  useEffect(() => {
    if (watchActivity && watchEf && efs.length > 0) {
      const ef = efs.find((e: any) => String(e.id) === String(watchEf))
      if (ef && parseFloat(watchActivity) > 0) {
        const co2e = (parseFloat(watchActivity) * ef.factor_value) / 1000
        setPreview({ co2e: co2e.toFixed(4), ef_value: ef.factor_value, ef_unit: ef.unit, ef_source: ef.source, ef_version: ef.version_tag })
      }
    } else { setPreview(null) }
  }, [watchActivity, watchEf, efs])

  const onManualSubmit = async (data: any) => {
    setLoading(true)
    try {
      // If "other" selected, use the custom_unit field as the actual unit
      const finalUnit = data.activity_unit === 'other' ? data.custom_unit : data.activity_unit
      await emissionsApi.create({
        ...data,
        activity_unit: finalUnit,
        category_id: parseInt(data.category_id),
        ef_id: parseInt(data.ef_id),
        activity_value: parseFloat(data.activity_value),
        input_method: 'manual',
      })
      toast.success('Emission record submitted!')
      reset()
      if (vendorCategory) setValue('category_id', String(vendorCategory))
      setPreview(null)
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Submission failed')
    } finally { setLoading(false) }
  }

  const onCsvUpload = async () => {
    if (!csvFile) return
    setLoading(true)
    try {
      const res = await emissionsApi.uploadCsv(csvFile)
      setCsvResult(res.data)
      if (res.data.created > 0) toast.success(`${res.data.created} records uploaded`)
      else toast.error('No records created. Check errors below.')
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Upload failed')
    } finally { setLoading(false) }
  }

  const downloadTemplate = async () => {
    const res = await reportsApi.csvTemplate()
    downloadBlob(new Blob([res.data], { type: 'text/csv' }), 'scope3_upload_template.csv')
  }

  const catOptions = Object.entries(SCOPE3_CATEGORIES).map(([id, name]) => ({ value: id, label: `${id}. ${name}` }))
  const efOptions  = efs.map((e: any) => ({
    value: String(e.id),
    label: `${e.material_type || e.subcategory} — ${e.factor_value} ${e.unit} (${e.source} ${e.version_tag})`
  }))

  return (
    <div>
      <SectionHeader
        title="Submit Emission Data"
        description="Record your activity data for Scope 3 emission calculation"
      />

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 bg-gray-100 rounded-xl w-fit">
        {(['manual', 'csv'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {t === 'manual' ? '✏️ Manual Entry' : '📄 CSV Upload'}
          </button>
        ))}
        <Link to="/activity-calculator"
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg text-brand-600 hover:bg-white hover:shadow-sm transition-all">
          <Calculator size={14}/> Calculate Activity Value
        </Link>
      </div>

      {tab === 'manual' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <form onSubmit={handleSubmit(onManualSubmit)} className="lg:col-span-2 card p-6 space-y-4">
            <h3 className="text-sm font-semibold text-gray-900">Activity Data</h3>

            <div className="grid grid-cols-2 gap-4">
              {/* Category */}
              <div className="col-span-2">
                <label className="label flex items-center">
                  Scope 3 Category *
                  <HelpTooltip title="Scope 3 Category"
                    content="Select the GHG Protocol category that best describes your supply or service. Your default category is pre-selected from your company profile."
                    link={{ label: 'View activity calculator', href: '/activity-calculator' }}/>
                </label>
                <select {...register('category_id', { required: 'Please select a category' })} className="input">
                  <option value="">Select category</option>
                  {catOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                {errors.category_id && <p className="mt-1 text-xs text-red-500">{errors.category_id.message as string}</p>}
                {vendorCategory && (
                  <p className="text-xs text-gray-400 mt-1">
                    Pre-filled from your profile (Cat {vendorCategory}). Change if submitting for a different category.
                  </p>
                )}
              </div>

              {/* Period Start */}
              <div>
                <label className="label">Period Start *</label>
                <input {...register('period_start', { required: 'Required' })} type="date" className="input"/>
                {errors.period_start && <p className="mt-1 text-xs text-red-500">{errors.period_start.message as string}</p>}
              </div>

              {/* Period End — only enabled after start, min = start date */}
              <div>
                <label className="label">Period End *</label>
                <input
                  {...register('period_end', {
                    required: 'Required',
                    validate: v => !watchStart || v >= watchStart || 'Must be after Period Start'
                  })}
                  type="date"
                  className="input disabled:opacity-40 disabled:cursor-not-allowed"
                  min={watchStart || undefined}
                  disabled={!watchStart}
                />
                {errors.period_end && <p className="mt-1 text-xs text-red-500">{errors.period_end.message as string}</p>}
                {!watchStart && <p className="text-xs text-gray-400 mt-1">Select Period Start first</p>}
              </div>

              {/* Activity Value */}
              <div>
                <label className="label flex items-center">
                  Activity Value *
                  <HelpTooltip
                    title="Activity Value"
                    content="The measurable quantity that drives emissions — e.g. tonnes of steel, km travelled, kWh used. Not sure what to enter?"
                    link={{ label: 'Open Activity Calculator', href: '/activity-calculator' }}
                  />
                </label>
                <input {...register('activity_value', {
                  required: 'Required',
                  min: { value: 0.001, message: 'Must be greater than 0' },
                })} type="number" step="any" className="input" placeholder="e.g. 500"/>
                {errors.activity_value && <p className="mt-1 text-xs text-red-500">{errors.activity_value.message as string}</p>}
                <p className="text-xs text-gray-400 mt-1">
                  Not sure? <Link to="/activity-calculator" className="text-brand-600 hover:underline">How to calculate →</Link>
                </p>
              </div>

              {/* Unit — dropdown */}
              <div>
                <label className="label flex items-center">
                  Unit *
                  <HelpTooltip title="Activity Unit" content="Select the unit that matches your activity value. Common units for your selected category are shown first. Choose 'Other' to type a custom unit."/>
                </label>
                <select {...register('activity_unit', { required: 'Required' })} className="input">
                  <option value="">Select unit</option>
                  {(unitOptions.length > 0 ? unitOptions : ALL_UNITS).map(u => <option key={u} value={u}>{u}</option>)}
                  <option value="other">Other (type below)</option>
                </select>
                {watchUnit === 'other' && (
                  <input
                    {...register('custom_unit', { required: watchUnit === 'other' ? 'Please specify your unit' : false })}
                    className="input mt-2"
                    placeholder="e.g. metric tons, pallets, litre-km"
                  />
                )}
                {errors.activity_unit && <p className="mt-1 text-xs text-red-500">{errors.activity_unit.message as string}</p>}
                {(errors as any).custom_unit && <p className="mt-1 text-xs text-red-500">{(errors as any).custom_unit.message as string}</p>}
              </div>

              {/* EF */}
              <div className="col-span-2">
                <label className="label flex items-center">
                  Emission Factor *
                  <HelpTooltip title="Emission Factor" content="A published conversion factor (DEFRA, IPCC, CPCB) that converts your activity into CO₂e. Select the one that best matches your material or activity type."/>
                </label>
                <select {...register('ef_id', { required: 'Please select an emission factor' })} className="input" disabled={!watchCat}>
                  <option value="">Select category first, then choose EF</option>
                  {efOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                {errors.ef_id && <p className="mt-1 text-xs text-red-500">{errors.ef_id.message as string}</p>}
              </div>

              {/* Data Quality */}
              <div>
                <label className="label flex items-center">
                  Data Quality
                  <HelpTooltip title="Data Quality" content="A = primary measured data (weigh-bridge, meter reading). B = estimated from averages or proxies. C = spend-based estimate. Higher quality = more credible reporting."/>
                </label>
                <select {...register('data_quality')} className="input">
                  <option value="A">A — Primary supplier data (measured)</option>
                  <option value="B">B — Proxy / industry average</option>
                  <option value="C">C — Spend-based estimate</option>
                </select>
              </div>

              <div>
                <label className="label">Notes</label>
                <input {...register('notes')} className="input" placeholder="Optional notes..."/>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-2.5">
              {loading ? <Spinner size="sm"/> : <><CheckCircle2 size={16}/> Submit Record</>}
            </button>
          </form>

          {/* Live preview */}
          <div className="space-y-4">
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Live Calculation Preview</h3>
              {preview ? (
                <div className="space-y-3">
                  <div className="p-3 bg-brand-50 rounded-xl text-center">
                    <p className="text-xs text-brand-600 mb-1">Estimated CO₂e</p>
                    <p className="text-2xl font-bold text-brand-800">{preview.co2e}</p>
                    <p className="text-xs text-brand-600">tCO₂e</p>
                  </div>
                  <div className="text-xs space-y-1.5 text-gray-600">
                    <div className="flex justify-between"><span>EF Value</span><span className="font-mono font-medium">{preview.ef_value} {preview.ef_unit}</span></div>
                    <div className="flex justify-between"><span>Source</span><span className="font-medium">{preview.ef_source}</span></div>
                    <div className="flex justify-between"><span>Version</span><span className="font-medium">{preview.ef_version}</span></div>
                  </div>
                  <p className="text-xs text-gray-400">Formula: Activity × EF ÷ 1000</p>
                </div>
              ) : (
                <div className="text-center py-6 text-gray-400 text-sm">
                  <p>Select a category, emission factor,</p>
                  <p>and enter a value to preview</p>
                </div>
              )}
            </div>

            <div className="card p-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Need help?</h3>
              <Link to="/activity-calculator"
                className="flex items-center gap-2 text-sm text-brand-600 hover:underline">
                <Calculator size={14}/> Activity Value Calculator
              </Link>
              <p className="text-xs text-gray-400 mt-1">
                Step-by-step guidance for measuring your activity data
              </p>
            </div>
          </div>
        </div>
      )}

      {tab === 'csv' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Upload CSV File</h3>
            <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-brand-300 transition-colors">
              <Upload size={32} className="mx-auto text-gray-300 mb-3"/>
              <p className="text-sm text-gray-600 mb-1">Drop your CSV file here</p>
              <p className="text-xs text-gray-400 mb-4">or click to browse</p>
              <input type="file" accept=".csv" onChange={e => { setCsvFile(e.target.files?.[0] || null); setCsvResult(null) }}
                className="hidden" id="csv-input"/>
              <label htmlFor="csv-input" className="btn-secondary cursor-pointer">
                <FileText size={14}/> Choose file
              </label>
              {csvFile && <p className="mt-3 text-xs text-brand-600 font-medium">{csvFile.name}</p>}
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={onCsvUpload} disabled={!csvFile || loading} className="btn-primary flex-1 justify-center">
                {loading ? <Spinner size="sm"/> : <><Upload size={14}/> Upload & Process</>}
              </button>
              <button onClick={downloadTemplate} className="btn-secondary">
                <FileText size={14}/> Template
              </button>
            </div>

            {csvResult && (
              <div className={`mt-4 p-4 rounded-xl border ${csvResult.errors?.length ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200'}`}>
                <div className="flex items-center gap-2 mb-2">
                  {csvResult.errors?.length ? <AlertTriangle size={16} className="text-amber-600"/> : <CheckCircle2 size={16} className="text-green-600"/>}
                  <p className="text-sm font-semibold">{csvResult.created} of {csvResult.total_rows} records created</p>
                </div>
                {csvResult.errors?.length > 0 && (
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {csvResult.errors.map((e: any, i: number) => (
                      <p key={i} className="text-xs text-amber-700">Row {e.row}: {e.error}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Required CSV Columns</h3>
            <div className="space-y-2">
              {[
                ['category_id', 'Number 1–15', true],
                ['period_start', 'YYYY-MM-DD', true],
                ['period_end', 'YYYY-MM-DD (must be ≥ period_start)', true],
                ['activity_value', 'Positive number', true],
                ['activity_unit', 'tonnes, km, kWh, INR...', true],
                ['ef_id', 'ID from EF Library', true],
                ['data_quality', 'A, B or C', false],
                ['notes', 'Any text', false],
              ].map(([col, desc, req]) => (
                <div key={col as string} className="flex items-start gap-2 p-2 rounded-lg bg-gray-50">
                  <code className="text-xs font-mono text-brand-700 mt-0.5 min-w-max">{col as string}</code>
                  <div className="flex-1">
                    <p className="text-xs text-gray-600">{desc as string}</p>
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${req ? 'bg-red-100 text-red-700' : 'bg-gray-200 text-gray-500'}`}>
                    {req ? 'required' : 'optional'}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-3 p-3 bg-amber-50 rounded-xl">
              <p className="text-xs text-amber-700">
                <strong>Validation:</strong> Each row is validated individually. Invalid rows are skipped and reported — valid rows are still created.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
