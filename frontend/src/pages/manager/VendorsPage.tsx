import { useEffect, useState } from 'react'
import { Plus, Mail, Building2, CheckCircle2, XCircle, Copy, Check, Eye, Trash2, X, Bell } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { usersApi } from '@/utils/api'
import api from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { PageLoader, SectionHeader, Modal, EmptyState, Spinner } from '@/components/ui'
import { REGION_LABELS, SCOPE3_CATEGORIES, formatCO2e } from '@/utils/constants'
import clsx from 'clsx'

export default function VendorsPage() {
  const { user } = useAuthStore()
  const [vendors, setVendors] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviting, setInviting] = useState(false)
  const [inviteResult, setInviteResult] = useState<any>(null)
  const [copied, setCopied] = useState(false)
  const [selectedVendor, setSelectedVendor] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [reminding, setReminding] = useState(false)
  const { register, handleSubmit, reset, formState: { errors } } = useForm()

  const sendBulkReminder = async () => {
    if (!confirm('Send a submission reminder email to all vendors who have not submitted this quarter?')) return
    setReminding(true)
    try {
      const res = await api.post('/vendor/bulk-reminder')
      toast.success(res.data.message)
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
    finally { setReminding(false) }
  }

  useEffect(() => { fetchVendors() }, [])

  const fetchVendors = async () => {
    setLoading(true)
    try { const res = await usersApi.listVendors(); setVendors(res.data) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const onInvite = async (data: any) => {
    setInviting(true)
    try {
      const res = await usersApi.inviteVendor(data)
      setInviteResult(res.data)
      toast.success(`Invitation sent to ${data.email}`)
      reset(); fetchVendors()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Invite failed') }
    finally { setInviting(false) }
  }

  const copyPassword = () => {
    if (inviteResult?.temp_password) {
      navigator.clipboard.writeText(inviteResult.temp_password)
      setCopied(true); setTimeout(() => setCopied(false), 2000)
    }
  }

  const toggleActive = async (id: number, current: boolean) => {
    try {
      await usersApi.update(id, { is_active: !current })
      toast.success(current ? 'Vendor deactivated' : 'Vendor activated')
      fetchVendors()
      if (selectedVendor?.id === id) setSelectedVendor((v: any) => ({ ...v, is_active: !current }))
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const deleteVendor = async (id: number, email: string) => {
    if (!confirm(`Deactivate vendor "${email}"? Their emission records will be preserved for audit purposes.`)) return
    try {
      await usersApi.delete(id)
      toast.success('Vendor deactivated')
      fetchVendors()
      if (selectedVendor?.id === id) setSelectedVendor(null)
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const openDetail = async (v: any) => {
    setSelectedVendor(v)  // show immediately with list data
    setDetailLoading(true)
    try {
      const res = await usersApi.getVendor(v.id)
      setSelectedVendor(res.data)
    } catch (e) { console.error(e) }
    finally { setDetailLoading(false) }
  }

  const regions = ['north', 'south', 'east', 'west', 'central']

  return (
    <div className="flex gap-5">
      {/* Main list */}
      <div className={clsx('flex-1 min-w-0 transition-all', selectedVendor && 'lg:max-w-[calc(100%-360px)]')}>
        <SectionHeader
          title="Vendor Management"
          description={user?.role === 'manager' ? `${REGION_LABELS[user.region!] || ''} vendors` : 'All vendors'}
          action={
            <div className="flex gap-2">
              <button onClick={sendBulkReminder} disabled={reminding} className="btn-secondary">
                {reminding ? <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"/> : <Bell size={16}/>}
                Send Reminder
              </button>
              <button onClick={() => { setInviteOpen(true); setInviteResult(null) }} className="btn-primary">
                <Plus size={16}/> Invite Vendor
              </button>
            </div>
          }
        />

        {loading ? <PageLoader /> : vendors.length === 0 ? (
          <EmptyState title="No vendors yet" description="Invite your first vendor to start collecting emission data."
            action={<button onClick={() => setInviteOpen(true)} className="btn-primary"><Plus size={16}/> Invite</button>} />
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="table-header">Company</th>
                  <th className="table-header">Region / City</th>
                  <th className="table-header">Material</th>
                  <th className="table-header">Records</th>
                  <th className="table-header">Onboarded</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {vendors.map((v: any) => (
                  <tr key={v.id}
                    className={clsx('hover:bg-gray-50 transition-colors cursor-pointer',
                      selectedVendor?.id === v.id && 'bg-brand-50')}
                    onClick={() => openDetail(v)}>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-brand-100 flex items-center justify-center flex-shrink-0">
                          <Building2 size={14} className="text-brand-600"/>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{v.company_name || '—'}</p>
                          <p className="text-xs text-gray-400">{v.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell text-sm">
                      <p className="capitalize">{v.region ? REGION_LABELS[v.region] || v.region : '—'}</p>
                      {v.city && <p className="text-xs text-gray-400">{v.city}</p>}
                    </td>
                    <td className="table-cell text-xs text-gray-600 max-w-[140px] truncate">{v.material_name || '—'}</td>
                    <td className="table-cell text-sm font-medium">{v.record_count ?? 0}</td>
                    <td className="table-cell">
                      {v.onboarding_complete
                        ? <span className="inline-flex items-center gap-1 text-xs text-green-600"><CheckCircle2 size={12}/> Done</span>
                        : <span className="text-xs text-amber-600">⏳ Pending</span>}
                    </td>
                    <td className="table-cell">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${v.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {v.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="table-cell" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        <button onClick={() => openDetail(v)}
                          className="p-1.5 hover:bg-brand-50 text-brand-600 rounded-lg transition-colors" title="View details">
                          <Eye size={14}/>
                        </button>
                        <button onClick={() => toggleActive(v.id, v.is_active)}
                          className={`p-1.5 rounded-lg transition-colors ${v.is_active ? 'hover:bg-amber-50 text-amber-500' : 'hover:bg-green-50 text-green-600'}`}
                          title={v.is_active ? 'Deactivate' : 'Activate'}>
                          {v.is_active ? <XCircle size={14}/> : <CheckCircle2 size={14}/>}
                        </button>
                        {(user?.role === 'admin' || user?.role === 'manager') && (
                          <button onClick={() => deleteVendor(v.id, v.email)}
                            className="p-1.5 hover:bg-red-50 text-red-400 rounded-lg transition-colors" title="Delete vendor">
                            <Trash2 size={14}/>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Vendor detail drawer */}
      {selectedVendor && (
        <div className="w-80 flex-shrink-0 hidden lg:block">
          <div className="card p-5 sticky top-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900">Vendor Details</h3>
              <button onClick={() => setSelectedVendor(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                <X size={15} className="text-gray-400"/>
              </button>
            </div>

            {detailLoading ? (
              <div className="flex justify-center py-8"><div className="w-5 h-5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"/></div>
            ) : (
              <div className="space-y-4">
                {/* Header */}
                <div className="p-3 bg-brand-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-white">
                        {selectedVendor.company_name?.[0] || selectedVendor.email?.[0] || '?'}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{selectedVendor.company_name || selectedVendor.email}</p>
                      {selectedVendor.trade_name && (
                        <p className="text-xs text-gray-500">({selectedVendor.trade_name})</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 bg-gray-50 rounded-xl text-center">
                    <p className="text-lg font-bold text-brand-700">{selectedVendor.record_count ?? 0}</p>
                    <p className="text-xs text-gray-500">Records</p>
                  </div>
                  <div className="p-2.5 bg-gray-50 rounded-xl text-center">
                    <p className="text-sm font-bold text-brand-700">{selectedVendor.total_co2e != null ? formatCO2e(selectedVendor.total_co2e) : '—'}</p>
                    <p className="text-xs text-gray-500">Total CO₂e</p>
                  </div>
                </div>

                {/* Details */}
                <div className="space-y-2">
                  {[
                    ['Email', selectedVendor.email],
                    ['Region', selectedVendor.region ? REGION_LABELS[selectedVendor.region] || selectedVendor.region : '—'],
                    ['City', selectedVendor.city || selectedVendor.profile?.city || '—'],
                    ['State', selectedVendor.state || selectedVendor.profile?.state || '—'],
                    ['GST', selectedVendor.gst_number || selectedVendor.profile?.gst_number || '—'],
                    ['NIC Code', selectedVendor.nic_code || selectedVendor.profile?.nic_code || '—'],
                    ['Category', (() => {
                      const cat = selectedVendor.material_category || selectedVendor.profile?.material_category
                      return cat ? `${cat}. ${SCOPE3_CATEGORIES[cat] || ''}` : '—'
                    })()],
                    ['Material', selectedVendor.material_name || selectedVendor.profile?.material_name || '—'],
                    ['Frequency', selectedVendor.supply_frequency || selectedVendor.profile?.supply_frequency || '—'],
                    ['Contact', selectedVendor.contact_name || selectedVendor.profile?.contact_name || '—'],
                    ['Phone', selectedVendor.contact_phone || selectedVendor.profile?.contact_phone || '—'],
                    ['Has Carbon Sys', (selectedVendor.has_own_carbon_system ?? selectedVendor.profile?.has_own_carbon_system) ? 'Yes' : 'No'],
                    ['Onboarded', selectedVendor.onboarding_complete ? '✅ Complete' : '⏳ Pending'],
                    ['Status', selectedVendor.is_active ? '🟢 Active' : '🔴 Inactive'],
                  ].map(([label, value]) => (
                    <div key={label as string} className="flex justify-between text-xs py-1 border-b border-gray-50 last:border-0">
                      <span className="text-gray-400 flex-shrink-0 mr-2">{label}</span>
                      <span className="text-gray-800 font-medium text-right break-all">{value as string}</span>
                    </div>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <button onClick={() => toggleActive(selectedVendor.id, selectedVendor.is_active)}
                    className={`flex-1 text-xs py-2 rounded-lg font-medium transition-colors ${selectedVendor.is_active ? 'bg-amber-50 text-amber-700 hover:bg-amber-100' : 'bg-green-50 text-green-700 hover:bg-green-100'}`}>
                    {selectedVendor.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  <button onClick={() => deleteVendor(selectedVendor.id, selectedVendor.email)}
                    className="flex-1 text-xs py-2 rounded-lg font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors">
                    Delete
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Invite modal */}
      <Modal open={inviteOpen} onClose={() => { setInviteOpen(false); setInviteResult(null); reset() }}
        title="Invite Vendor" size="sm">
        {!inviteResult ? (
          <form onSubmit={handleSubmit(onInvite)} className="space-y-4">
            <div>
              <label className="label">Vendor Email *</label>
              <input {...register('email', { required: 'Required' })} type="email" className="input" placeholder="vendor@company.com"/>
              {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message as string}</p>}
            </div>
            <div>
              <label className="label">Assign Region *</label>
              <select {...register('region', { required: 'Required' })} className="input"
                defaultValue={user?.role === 'manager' ? user.region || '' : ''}>
                <option value="">Select region</option>
                {regions.map(r => (
                  <option key={r} value={r} disabled={user?.role === 'manager' && r !== user.region}>
                    {REGION_LABELS[r]}
                  </option>
                ))}
              </select>
              {errors.region && <p className="mt-1 text-xs text-red-500">{errors.region.message as string}</p>}
            </div>
            <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-700">
              <Mail size={12} className="inline mr-1"/>
              An invitation email will be sent. The temp password is always shown here for manual sharing.
            </div>
            <div className="flex gap-3 pt-1">
              <button type="button" onClick={() => { setInviteOpen(false); reset() }} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button type="submit" disabled={inviting} className="btn-primary flex-1 justify-center">
                {inviting ? <Spinner size="sm"/> : <><Mail size={14}/> Send Invite</>}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-100 rounded-xl">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle2 size={16} className="text-green-600"/>
                <p className="text-sm font-semibold text-green-800">Invitation sent!</p>
              </div>
              <p className="text-xs text-green-700">Email dispatched to <strong>{inviteResult.email}</strong></p>
            </div>
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Temporary Password</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 font-mono text-sm font-bold text-gray-900 bg-white border border-gray-200 rounded-lg px-3 py-2">
                  {inviteResult.temp_password}
                </code>
                <button onClick={copyPassword} className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  {copied ? <Check size={16} className="text-green-600"/> : <Copy size={16} className="text-gray-500"/>}
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-2">⚠️ Expires in 48 hours.</p>
            </div>
            <button onClick={() => { setInviteOpen(false); setInviteResult(null) }} className="btn-primary w-full justify-center">Done</button>
          </div>
        )}
      </Modal>
    </div>
  )
}
