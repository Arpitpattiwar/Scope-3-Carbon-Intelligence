import { useState } from 'react'
import { Download, FileSpreadsheet, FileText, BarChart2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { reportsApi } from '@/utils/api'
import api from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { SectionHeader, Select } from '@/components/ui'
import { downloadBlob } from '@/utils/constants'
import { URLS } from '@/utils/urls'

const YEARS = Array.from({ length: 5 }, (_, i) => {
  const y = new Date().getFullYear() - i
  return { value: String(y), label: `FY ${y}` }
})

export default function ReportsPage() {
  const { user } = useAuthStore()
  const [year, setYear]       = useState(String(new Date().getFullYear()))
  const [downloading, setDownloading] = useState<string | null>(null)

  const dl = async (key: string, fn: () => Promise<any>, filename: string, type: string) => {
    setDownloading(key)
    try {
      const res = await fn()
      downloadBlob(new Blob([res.data], { type }), filename)
      toast.success('Downloaded')
    } catch { toast.error('Download failed') }
    finally { setDownloading(null) }
  }

  const isVendor = user?.role === 'vendor'

  const adminReports = [
    {
      key: 'excel',
      title: 'GRI 305 Scope 3 Disclosure',
      description: 'Full emission records with activity data, emission factors, calculation trace, and methodology appendix. GHG Protocol aligned.',
      format: 'XLSX', icon: <FileSpreadsheet size={20} className="text-green-600"/>, bg: 'bg-green-50',
      standard: 'GRI 305 · GHG Protocol',
      action: () => reportsApi.downloadExcel({ year: parseInt(year) }),
      filename: `scope3_GRI305_${year}.xlsx`,
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
    {
      key: 'brsr',
      title: 'BRSR — Principle 6 (Environment)',
      description: 'India SEBI-mandated Business Responsibility & Sustainability Report, Principle 6 emissions section. For listed companies.',
      format: 'CSV', icon: <BarChart2 size={20} className="text-blue-600"/>, bg: 'bg-blue-50',
      standard: 'SEBI BRSR 2023',
      action: () => api.get('/vendor/brsr-export', { params: { year: parseInt(year) }, responseType: 'blob' }),
      filename: `BRSR_Scope3_${year}.csv`,
      type: 'text/csv',
    },
    {
      key: 'template',
      title: 'Data Upload Template',
      description: 'Standardised CSV template with column headers and example row. Distribute to vendors for bulk data collection.',
      format: 'CSV', icon: <FileText size={20} className="text-gray-500"/>, bg: 'bg-gray-50',
      standard: 'Internal template',
      action: () => reportsApi.csvTemplate(),
      filename: 'scope3_upload_template.csv',
      type: 'text/csv',
    },
  ]

  const vendorReports = [
    {
      key: 'vendor-csv',
      title: 'My Emission Data Export',
      description: 'All your submitted emission records in CSV format. Use this for your own sustainability reporting or audits.',
      format: 'CSV', icon: <FileSpreadsheet size={20} className="text-green-600"/>, bg: 'bg-green-50',
      standard: 'Vendor data export',
      action: () => api.get('/vendor/export-csv', { params: { year: parseInt(year) }, responseType: 'blob' }),
      filename: `my_emissions_${year}.csv`,
      type: 'text/csv',
    },
    {
      key: 'brsr-vendor',
      title: 'BRSR Scope 3 Section',
      description: 'SEBI BRSR Principle 6 export with your Scope 3 emissions data.',
      format: 'CSV', icon: <BarChart2 size={20} className="text-blue-600"/>, bg: 'bg-blue-50',
      standard: 'SEBI BRSR 2023',
      action: () => api.get('/vendor/brsr-export', { params: { year: parseInt(year) }, responseType: 'blob' }),
      filename: `BRSR_Scope3_${year}.csv`,
      type: 'text/csv',
    },
  ]

  const reports = isVendor ? vendorReports : adminReports

  return (
    <div>
      <SectionHeader
        title="Reports & Disclosures"
        description="Download GRI-305, BRSR, and data templates"
        action={<Select options={YEARS} value={year} onChange={setYear} className="w-28"/>}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {reports.map(r => (
          <div key={r.key} className="card p-6 flex flex-col gap-4">
            <div className="flex items-start gap-4">
              <div className={`w-10 h-10 rounded-xl ${r.bg} flex items-center justify-center flex-shrink-0`}>{r.icon}</div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-gray-900">{r.title}</h3>
                <p className="text-xs text-gray-500 mt-1 leading-relaxed">{r.description}</p>
                <span className="inline-flex items-center gap-1 mt-2 text-xs text-gray-400">📋 {r.standard}</span>
              </div>
            </div>
            <button onClick={() => dl(r.key, r.action, r.filename, r.type)}
              disabled={downloading === r.key} className="btn-primary justify-center">
              {downloading === r.key
                ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/>
                : <><Download size={14}/> Download {r.format}</>}
            </button>
          </div>
        ))}
      </div>

      {/* Methodology references — verified working URLs */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Standards & Methodology References</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            {
              name: 'GHG Protocol Scope 3 Standard',
              url: URLS.ghgProtocolScope3,
              badge: 'Required',
              note: 'Corporate Value Chain (Scope 3) Accounting Standard'
            },
            {
              name: 'GRI 305 Emissions Disclosure',
              url: URLS.griStandards,
              badge: 'Required',
              note: 'GRI Topic Standards — Emissions section'
            },
            {
              name: 'DEFRA 2024 Conversion Factors',
              url: URLS.defraConversionFactors,
              badge: 'EF Source',
              note: 'UK Government GHG conversion factors for company reporting'
            },
            {
              name: 'IPCC AR6 Emission Factors',
              url: URLS.ipccAr6,
              badge: 'EF Source',
              note: 'Sixth Assessment Report Working Group III — Mitigation'
            },
            {
              name: 'SEBI BRSR Framework 2023',
              url: URLS.sebiBrsr,
              badge: 'India',
              note: 'SEBI circular on BRSR for listed entities'
            },
            {
              name: 'CPCB India Emission Factors',
              url: URLS.cpcb,
              badge: 'India',
              note: 'Central Pollution Control Board — India-specific EFs'
            },
          ].map(s => (
            <a key={s.name} href={s.url} target="_blank" rel="noopener noreferrer"
              className="flex items-start justify-between p-3 rounded-xl bg-gray-50 hover:bg-brand-50 transition-colors group">
              <div className="flex-1 min-w-0 mr-2">
                <p className="text-sm text-gray-700 group-hover:text-brand-700 font-medium">{s.name}</p>
                <p className="text-xs text-gray-400 mt-0.5 truncate">{s.note}</p>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-white border border-gray-200 text-gray-500 flex-shrink-0">{s.badge}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
