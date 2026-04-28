import { useEffect, useState } from 'react'
import { Search, Download } from 'lucide-react'
import { auditApi } from '@/utils/api'
import { PageLoader, SectionHeader, Select, EmptyState } from '@/components/ui'
import { downloadBlob } from '@/utils/constants'
import toast from 'react-hot-toast'

const ACTION_COLORS: Record<string, string> = {
  LOGIN:                  'bg-gray-100 text-gray-600',
  CREATE_EMISSION_RECORD: 'bg-blue-100 text-blue-700',
  CSV_UPLOAD:             'bg-blue-100 text-blue-700',
  STATUS_UPDATE:          'bg-amber-100 text-amber-700',
  CREATE_USER:            'bg-purple-100 text-purple-700',
  INVITE_VENDOR:          'bg-brand-100 text-brand-700',
  VENDOR_ONBOARDING:      'bg-green-100 text-green-700',
  CHANGE_PASSWORD:        'bg-gray-100 text-gray-600',
  UPDATE_PROFILE:         'bg-gray-100 text-gray-600',
  CHANGE_EMAIL:           'bg-gray-100 text-gray-600',
  CREATE_EF:              'bg-purple-100 text-purple-700',
  DEACTIVATE_EF:          'bg-red-100 text-red-700',
  LOCK_PERIOD:            'bg-red-100 text-red-700',
  UPDATE_USER:            'bg-amber-100 text-amber-700',
  UPDATE_VENDOR_PROFILE:  'bg-amber-100 text-amber-700',
}

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [actionFilter, setActionFilter] = useState('')
  const [search, setSearch] = useState('')
  const [exporting, setExporting] = useState(false)

  useEffect(() => { fetchLogs() }, [actionFilter])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params: any = { limit: 200 }
      if (actionFilter) params.action = actionFilter
      const res = await auditApi.logs(params)
      setLogs(res.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const exportCsv = async () => {
    setExporting(true)
    try {
      const res = await auditApi.exportCsv()
      downloadBlob(new Blob([res.data], { type: 'text/csv' }), 'audit_log.csv')
      toast.success('Audit log exported')
    } catch { toast.error('Export failed') }
    finally { setExporting(false) }
  }

  const filtered = logs.filter(l => {
    if (!search) return true
    const s = search.toLowerCase()
    return l.action?.toLowerCase().includes(s) ||
      l.description?.toLowerCase().includes(s) ||
      l.user?.email?.toLowerCase().includes(s) ||
      String(l.record_id || '').includes(s)
  })

  const actionOptions = [
    { value: '', label: 'All Actions' },
    ...Object.keys(ACTION_COLORS).map(a => ({ value: a, label: a.replace(/_/g,' ') }))
  ]

  return (
    <div>
      <SectionHeader title="Audit Log" description="Complete immutable record of all platform actions"
        action={
          <button onClick={exportCsv} disabled={exporting} className="btn-secondary">
            {exporting ? <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"/> : <Download size={14}/>}
            Export CSV
          </button>
        }
      />

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by user, action, description..." className="input pl-9"/>
        </div>
        <Select options={actionOptions} value={actionFilter} onChange={setActionFilter} className="w-52"/>
      </div>

      {loading ? <PageLoader /> : filtered.length === 0 ? (
        <EmptyState title="No audit logs" description="Actions will be logged here automatically."/>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="table-header">Timestamp</th>
                <th className="table-header">User</th>
                <th className="table-header">Action</th>
                <th className="table-header">Table / Record</th>
                <th className="table-header">Description</th>
                <th className="table-header">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((log: any) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="table-cell text-xs text-gray-500 whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString('en-IN', { dateStyle:'short', timeStyle:'short' })}
                  </td>
                  <td className="table-cell">
                    <p className="text-xs font-medium text-gray-800">{log.user?.full_name || log.user?.email || `#${log.user_id}`}</p>
                    <p className="text-xs text-gray-400 capitalize">{log.user?.role}</p>
                  </td>
                  <td className="table-cell">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ACTION_COLORS[log.action] || 'bg-gray-100 text-gray-600'}`}>
                      {log.action?.replace(/_/g,' ')}
                    </span>
                  </td>
                  <td className="table-cell text-xs font-mono text-gray-500">
                    {log.table_name && <span>{log.table_name}{log.record_id ? ` #${log.record_id}` : ''}</span>}
                  </td>
                  <td className="table-cell text-xs text-gray-600 max-w-xs truncate">{log.description || '—'}</td>
                  <td className="table-cell text-xs font-mono text-gray-400">{log.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
