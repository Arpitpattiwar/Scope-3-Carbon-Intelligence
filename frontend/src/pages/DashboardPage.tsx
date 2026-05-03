import { useEffect, useState } from 'react'
import { Factory, TrendingUp, BarChart3, AlertTriangle, Target, Clock, BrainCircuit, Info } from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, ReferenceLine,
  ComposedChart, Line, Legend,
} from 'recharts'
import { dashboardApi, targetsApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { KpiCard, PageLoader, SectionHeader, Select, Modal, Spinner } from '@/components/ui'
import { CHART_COLORS, REGION_LABELS, formatCO2e } from '@/utils/constants'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'

const YEARS = Array.from({ length: 5 }, (_, i) => {
  const y = new Date().getFullYear() - i
  return { value: String(y), label: String(y) }
})
const FREQ_OPTIONS = [
  { value: 'monthly',   label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'yearly',    label: 'Yearly' },
]
const SECTOR_OPTIONS = [
  { value: 'coal',   label: 'Industrial (Coal proxy)' },
  { value: 'oil',    label: 'Transport (Oil proxy)' },
  { value: 'gas',    label: 'Energy (Gas proxy)' },
  { value: 'cement', label: 'Construction (Cement proxy)' },
]

export default function DashboardPage() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [year, setYear]         = useState('2024')
  const [freq, setFreq]         = useState('monthly')
  const [region, setRegion]     = useState('')
  const [loading, setLoading]   = useState(true)
  const [summary, setSummary]   = useState<any>(null)
  const [categories, setCategories] = useState<any[]>([])
  const [regions, setRegions]   = useState<any[]>([])
  const [trend, setTrend]       = useState<any[]>([])
  const [topVendors, setTopVendors] = useState<any[]>([])
  const [engagement, setEngagement] = useState<any[]>([])
  const [targets, setTargets]   = useState<any[]>([])
  const [targetModal, setTargetModal] = useState(false)
  const [savingTarget, setSavingTarget] = useState(false)
  // Forecast state
  const [forecastSector, setForecastSector] = useState('coal')
  const [forecastData, setForecastData]     = useState<any>(null)
  const [forecastLoading, setForecastLoading] = useState(false)
  const [forecastError, setForecastError]   = useState<string | null>(null)

  const { register, handleSubmit, reset } = useForm()

  useEffect(() => { fetchAll() }, [year, freq, region])
  useEffect(() => {
    targetsApi.list(parseInt(year)).then(r => setTargets(r.data)).catch(() => {})
  }, [year])

  useEffect(() => { fetchForecast(forecastSector) }, [forecastSector])

  const fetchForecast = async (sector: string) => {
    setForecastLoading(true)
    setForecastError(null)
    try {
      const r = await dashboardApi.forecast(sector)
      setForecastData(r.data)
    } catch (e: any) {
      setForecastError(e.response?.data?.detail || 'Forecast service unavailable')
      setForecastData(null)
    } finally { setForecastLoading(false) }
  }

  const fetchAll = async () => {
    setLoading(true)
    try {
      const params: any = { year: parseInt(year) }
      if (region) params.region = region
      const [s, c, r, t, tv] = await Promise.all([
        dashboardApi.summary(params),
        dashboardApi.categoryBreakdown(params),
        dashboardApi.regionBreakdown({ year: parseInt(year) }),
        dashboardApi.trend({ ...params, frequency: freq }),
        dashboardApi.topVendors(params),
      ])
      setSummary(s.data)
      setCategories(c.data)
      setRegions(r.data)
      setTrend(t.data)
      setTopVendors(tv.data)
      if (['admin', 'manager'].includes(user?.role || '')) {
        const eng = await dashboardApi.vendorEngagement()
        setEngagement(eng.data.slice(0, 8))
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const onCreateTarget = async (data: any) => {
    setSavingTarget(true)
    try {
      await targetsApi.create({ ...data, year: parseInt(year), target_co2e: parseFloat(data.target_co2e) })
      toast.success('Target set')
      setTargetModal(false); reset()
      const r = await targetsApi.list(parseInt(year)); setTargets(r.data)
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
    finally { setSavingTarget(false) }
  }

  if (loading && !summary) return <PageLoader />

  const regionOptions = [
    { value: '', label: 'All Regions' },
    ...['north','south','east','west','central'].map(r => ({ value: r, label: REGION_LABELS[r] }))
  ]

  const activeTarget = targets.find(t => !t.region || t.region === region || t.region === user?.region)
  const targetPerPeriod = activeTarget && trend.length > 0
    ? activeTarget.target_co2e / trend.length
    : null

  const pendingRecords = summary?.pending_records ?? 0

  return (
    <div>
      <SectionHeader
        title="Emissions Dashboard"
        description={`Scope 3 overview · FY${year} · GHG Protocol aligned`}
        action={
          <div className="flex items-center gap-2">
            {['admin','auditor'].includes(user?.role || '') && (
              <Select options={regionOptions} value={region} onChange={setRegion} className="w-36 text-sm"/>
            )}
            <Select options={YEARS} value={year} onChange={setYear} className="w-28 text-sm"/>
            {user?.role === 'admin' && (
              <button onClick={() => setTargetModal(true)} className="btn-secondary text-sm">
                <Target size={14}/> Set Target
              </button>
            )}
          </div>
        }
      />

      {/* Pending records action banner */}
      {['admin','manager'].includes(user?.role || '') && pendingRecords > 0 && (
        <button onClick={() => navigate('/emissions?status=submitted')}
          className="w-full mb-4 p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-3 hover:bg-amber-100 transition-colors text-left">
          <Clock size={16} className="text-amber-600 flex-shrink-0"/>
          <p className="text-sm text-amber-800 flex-1">
            <strong>{pendingRecords}</strong> emission record{pendingRecords > 1 ? 's' : ''} awaiting your approval
          </p>
          <span className="text-xs text-amber-600 font-medium">Review →</span>
        </button>
      )}

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard
          label="Total Scope 3"
          value={summary ? formatCO2e(summary.total_co2e) : '—'}
          change={summary?.yoy_change_pct}
          icon={<Factory size={16}/>}
        />
        <KpiCard
          label="Records Submitted"
          value={summary?.record_count ?? '—'}
          icon={<BarChart3 size={16}/>}
          color="blue"
        />
        <KpiCard
          label="Top Category"
          value={categories[0]?.category_name?.split(' ').slice(0, 2).join(' ') ?? '—'}
          unit={categories[0] ? `${categories[0].percentage}%` : ''}
          icon={<TrendingUp size={16}/>}
          color="amber"
        />
        {activeTarget ? (
          <KpiCard
            label="vs Annual Target"
            value={summary ? `${Math.round((summary.total_co2e / activeTarget.target_co2e) * 100)}%` : '—'}
            unit="of target"
            change={summary
              ? Math.round(((summary.total_co2e - activeTarget.target_co2e) / activeTarget.target_co2e) * 100)
              : null}
            icon={<Target size={16}/>}
            color="green"
          />
        ) : (
          <KpiCard
            label="Pending Approval"
            value={pendingRecords}
            unit="records"
            icon={<AlertTriangle size={16}/>}
            color="amber"
          />
        )}
      </div>

      {/* Row 2: Trend + Category donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Emission Trend</h3>
              {activeTarget && (
                <p className="text-xs text-gray-400 mt-0.5">
                  Dashed = annual target ({formatCO2e(activeTarget.target_co2e)})
                </p>
              )}
            </div>
            <Select options={FREQ_OPTIONS} value={freq} onChange={setFreq} className="w-32 text-xs"/>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={trend}>
              <defs>
                <linearGradient id="co2grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#1aa876" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="#1aa876" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0"/>
              <XAxis dataKey="period" tick={{ fontSize: 11 }}/>
              <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${v}t`}/>
              <Tooltip formatter={(v: any) => [`${Number(v).toFixed(2)} tCO₂e`, 'Emissions']}/>
              <Area type="monotone" dataKey="total_co2e" stroke="#1aa876" strokeWidth={2} fill="url(#co2grad)"/>
              {targetPerPeriod && (
                <ReferenceLine y={targetPerPeriod} stroke="#f59e0b" strokeDasharray="5 5"
                  label={{ value: 'Target', position: 'right', fontSize: 10, fill: '#f59e0b' }}/>
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Category Share</h3>
          {categories.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={categories.slice(0, 6)} dataKey="total_co2e"
                    nameKey="category_name" cx="50%" cy="50%"
                    innerRadius={45} outerRadius={70} paddingAngle={2}>
                    {categories.slice(0, 6).map((_: any, i: number) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]}/>
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: any) => [`${Number(v).toFixed(2)} tCO₂e`]}/>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5 mt-2">
                {categories.slice(0, 5).map((c: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: CHART_COLORS[i] }}/>
                      <span className="text-gray-600 truncate max-w-[110px]">
                        {c.category_name}
                      </span>
                    </div>
                    <span className="font-medium text-gray-800 ml-1">{c.percentage}%</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-40 text-sm text-gray-400">
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Row 3: Category bar + Region/Engagement */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">
            Emissions by Category (tCO₂e)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={categories.slice(0, 8)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false}/>
              <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={v => `${v}t`}/>
              <YAxis type="category" dataKey="category_id" tick={{ fontSize: 10 }} width={28}
                tickFormatter={v => `C${v}`}/>
              <Tooltip
                formatter={(v: any) => [`${Number(v).toFixed(2)} tCO₂e`]}
                labelFormatter={(l: any) => `Category ${l}`}/>
              <Bar dataKey="total_co2e" radius={[0, 4, 4, 0]}>
                {categories.slice(0, 8).map((_: any, i: number) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]}/>
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {['admin','auditor'].includes(user?.role || '') && regions.length > 0 ? (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Emissions by Region</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={regions}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0"/>
                <XAxis dataKey="region" tick={{ fontSize: 11 }}
                  tickFormatter={v => v.charAt(0).toUpperCase() + v.slice(1)}/>
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${v}t`}/>
                <Tooltip formatter={(v: any) => [`${Number(v).toFixed(2)} tCO₂e`, 'Emissions']}/>
                <Bar dataKey="total_co2e" fill="#1aa876" radius={[4, 4, 0, 0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : user?.role === 'manager' && engagement.length > 0 ? (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Vendor Engagement</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={engagement}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0"/>
                <XAxis dataKey="company_name" tick={{ fontSize: 9 }}
                  tickFormatter={v => v?.slice(0, 8) || ''}/>
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }}/>
                <Tooltip/>
                <Bar dataKey="engagement_score" fill="#38c28d" radius={[4, 4, 0, 0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : null}
      </div>


      {/* AI Forecast Panel */}
      <div className="card p-5 mb-4">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <BrainCircuit size={15} className="text-brand-600"/>
            <h3 className="text-sm font-semibold text-gray-900">AI Emission Forecast — Next 3 Months</h3>
          </div>
          <Select options={SECTOR_OPTIONS} value={forecastSector} onChange={v => setForecastSector(v)} className="w-52 text-xs"/>
        </div>
        <div className="flex items-start gap-2 mb-3 p-2 bg-amber-50 border border-amber-100 rounded-lg">
          <Info size={13} className="text-amber-500 mt-0.5 flex-shrink-0"/>
          <p className="text-xs text-amber-700 leading-relaxed">
            Uses macro India sector emission patterns as a proxy scaled to your last 12 months. Shows trend direction — not exact quantities. 90% bands are indicative (PI coverage ~63% in backtesting).
          </p>
        </div>
        {forecastLoading && (
          <div className="flex items-center justify-center h-48 gap-2 text-sm text-gray-400">
            <Spinner size="sm"/> Running LSTM inference…
          </div>
        )}
        {!forecastLoading && forecastError && (
          <div className="flex items-center justify-center h-48 text-sm text-red-500">{forecastError}</div>
        )}
        {!forecastLoading && forecastData && !forecastData.forecast_available && (
          <div className="flex items-center justify-center h-48 text-center text-sm text-gray-400 px-8">{forecastData.reason}</div>
        )}
        {!forecastLoading && forecastData?.forecast_available && (() => {
          const hist = (forecastData.history || []).map((h: any) => ({
            period: h.period, actual: h.value, forecast: null, lower: null, upper: null,
          }))
          const fc = (forecastData.forecast_periods || []).map((p: string, i: number) => ({
            period: p, actual: null,
            forecast: forecastData.forecast[i] ?? null,
            lower:    forecastData.lower_90[i]  ?? null,
            upper:    forecastData.upper_90[i]  ?? null,
          }))
          const chartData = [...hist.slice(-12), ...fc]
          return (
            <>
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={chartData}>
                  <defs>
                    <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#1aa876" stopOpacity={0.18}/>
                      <stop offset="95%" stopColor="#1aa876" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0"/>
                  <XAxis dataKey="period" tick={{ fontSize: 10 }}/>
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${v}t`}/>
                  <Tooltip formatter={(value: any, name: string) => {
                    if (value === null || value === undefined) return null
                    const labels: Record<string,string> = {actual:'Actual (tCO₂e)',forecast:'Forecast (tCO₂e)',lower:'90% PI Lower',upper:'90% PI Upper'}
                    return [`${Number(value).toFixed(3)}`, labels[name] ?? name]
                  }}/>
                  <Legend iconSize={10}/>
                  <Area type="monotone" dataKey="actual" stroke="#1aa876" strokeWidth={2} fill="url(#histGrad)" connectNulls={false} dot={false}/>
                  <Line type="monotone" dataKey="forecast" stroke="#6366f1" strokeWidth={2.5} strokeDasharray="6 3" dot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }} connectNulls={false}/>
                  <Line type="monotone" dataKey="upper" stroke="#6366f1" strokeWidth={0.5} strokeDasharray="3 3" dot={false} connectNulls={false}/>
                  <Line type="monotone" dataKey="lower" stroke="#6366f1" strokeWidth={0.5} strokeDasharray="3 3" dot={false} connectNulls={false}/>
                  {chartData.find((d: any) => d.forecast !== null) && (
                    <ReferenceLine x={chartData.find((d: any) => d.forecast !== null)?.period}
                      stroke="#6366f1" strokeDasharray="4 2"
                      label={{ value: 'Forecast →', position: 'top', fontSize: 9, fill: '#6366f1' }}/>
                  )}
                </ComposedChart>
              </ResponsiveContainer>
              <div className="flex gap-3 mt-3 flex-wrap">
                {forecastData.forecast_periods.map((p: string, i: number) => (
                  <div key={p} className="flex-1 min-w-[90px] bg-indigo-50 border border-indigo-100 rounded-lg p-3 text-center">
                    <p className="text-xs text-indigo-400 mb-1">{p}</p>
                    <p className="text-sm font-semibold text-indigo-700">{formatCO2e(forecastData.forecast[i])}</p>
                    <p className="text-xs text-indigo-300 mt-0.5">[{formatCO2e(forecastData.lower_90[i])} – {formatCO2e(forecastData.upper_90[i])}]</p>
                  </div>
                ))}
                <div className="flex items-center gap-1 ml-auto self-end">
                  <span className="text-xs text-gray-400">Model:</span>
                  <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-0.5 rounded">{forecastData.model_used || 'LSTM'}</span>
                </div>
              </div>
            </>
          )
        })()}
      </div>

      {/* Top vendors table */}
      {topVendors.length > 0 && ['admin','manager','auditor'].includes(user?.role || '') && (
        <div className="card mb-4">
          <div className="p-5 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">Top Vendors by Emissions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="table-header">Vendor</th>
                  <th className="table-header">Region</th>
                  <th className="table-header">Total CO₂e</th>
                  <th className="table-header">Records</th>
                  <th className="table-header">Last Submission</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {topVendors.map((v: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50 transition-colors">
                    <td className="table-cell font-medium">{v.company_name}</td>
                    <td className="table-cell capitalize">{v.region || '—'}</td>
                    <td className="table-cell font-mono font-medium text-brand-700">
                      {formatCO2e(v.total_co2e)}
                    </td>
                    <td className="table-cell">{v.record_count}</td>
                    <td className="table-cell text-xs text-gray-500">
                      {v.last_submission
                        ? new Date(v.last_submission).toLocaleDateString('en-IN')
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Vendor own cards */}
      {user?.role === 'vendor' && summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Emission Intensity</h3>
            <p className="text-2xl font-semibold text-brand-700">
              {summary.record_count > 0
                ? (summary.total_co2e / summary.record_count).toFixed(3)
                : '—'}
            </p>
            <p className="text-xs text-gray-400 mt-1">tCO₂e per record</p>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Data Quality</h3>
            <div className="space-y-2">
              {['A','B','C'].map(q => (
                <div key={q} className="flex items-center justify-between">
                  <span className={`badge-${q}`}>
                    {q === 'A' ? 'Primary' : q === 'B' ? 'Proxy' : 'Estimated'}
                  </span>
                  <span className="text-sm font-medium text-gray-700">
                    {summary.data_quality_distribution?.[q] ?? 0}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">YoY Change</h3>
            <p className={`text-2xl font-semibold ${
              (summary.yoy_change_pct ?? 0) > 0 ? 'text-red-600' : 'text-green-600'
            }`}>
              {summary.yoy_change_pct !== null && summary.yoy_change_pct !== undefined
                ? `${summary.yoy_change_pct > 0 ? '+' : ''}${summary.yoy_change_pct}%`
                : '—'}
            </p>
            <p className="text-xs text-gray-400 mt-1">vs previous year</p>
          </div>
        </div>
      )}

      {/* Set Target Modal */}
      <Modal open={targetModal} onClose={() => { setTargetModal(false); reset() }}
        title="Set Emission Target" size="sm">
        <form onSubmit={handleSubmit(onCreateTarget)} className="space-y-4">
          <div>
            <label className="label">Label</label>
            <input {...register('label')} className="input" placeholder={`FY${year} Reduction Target`}/>
          </div>
          <div>
            <label className="label">Annual Target (tCO₂e) *</label>
            <input {...register('target_co2e', { required: true })} type="number" step="any"
              className="input" placeholder="e.g. 10000"/>
          </div>
          <div>
            <label className="label">Region (leave empty for all regions)</label>
            <select {...register('region')} className="input">
              <option value="">All Regions</option>
              {['north','south','east','west','central'].map(r => (
                <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
              ))}
            </select>
          </div>
          <p className="text-xs text-gray-400">
            Appears as a dashed reference line on the trend chart.
          </p>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => { setTargetModal(false); reset() }}
              className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={savingTarget} className="btn-primary flex-1 justify-center">
              {savingTarget ? <Spinner size="sm"/> : <><Target size={14}/> Set Target</>}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
