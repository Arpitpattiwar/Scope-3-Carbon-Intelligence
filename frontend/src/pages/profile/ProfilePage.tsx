import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { User, Mail, Lock, Building2, Phone, Save, ShieldCheck } from 'lucide-react'
import { profileApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { SectionHeader, Spinner } from '@/components/ui'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { SCOPE3_CATEGORIES, REGION_LABELS } from '@/utils/constants'

type ConfirmState = { open: boolean; title: string; message: string; onConfirm: () => void }

const INITIAL_CONFIRM: ConfirmState = { open: false, title: '', message: '', onConfirm: () => {} }

export default function ProfilePage() {
  const { user, updateUser } = useAuthStore()
  const [tab, setTab]             = useState<'info'|'security'|'vendor'>('info')
  const [saving, setSaving]       = useState(false)
  const [vendorProfile, setVendorProfile] = useState<any>(null)
  const [confirm, setConfirm]     = useState<ConfirmState>(INITIAL_CONFIRM)

  const infoForm   = useForm({ defaultValues: { full_name: user?.full_name || '', phone: (user as any)?.phone || '', designation: (user as any)?.designation || '' } })
  const pwForm     = useForm()
  const emailForm  = useForm()
  const vendorForm = useForm()

  useEffect(() => {
    if (user?.role === 'vendor') {
      profileApi.getVendorDetails().then(r => { setVendorProfile(r.data); vendorForm.reset(r.data) }).catch(() => {})
    }
  }, [user])

  const ask = (title: string, message: string, onConfirm: () => void) =>
    setConfirm({ open: true, title, message, onConfirm })
  const closeConfirm = () => setConfirm(INITIAL_CONFIRM)

  const doSave = async (fn: () => Promise<void>) => {
    setSaving(true)
    try { await fn() }
    finally { setSaving(false); closeConfirm() }
  }

  const onInfoSave = async (data: any) => {
    await doSave(async () => {
      const res = await profileApi.update(data)
      updateUser({ ...user!, ...res.data })
      toast.success('Profile updated')
    })
  }

  const onPasswordSave = async (data: any) => {
    if (data.new_password !== data.confirm_password) { toast.error('Passwords do not match'); return }
    await doSave(async () => {
      await profileApi.changePassword({ current_password: data.current_password, new_password: data.new_password })
      toast.success('Password changed'); pwForm.reset()
    })
  }

  const onEmailSave = async (data: any) => {
    await doSave(async () => {
      await profileApi.changeEmail(data)
      updateUser({ ...user!, email: data.new_email })
      toast.success('Email updated'); emailForm.reset()
    })
  }

  const onVendorSave = async (data: any) => {
    await doSave(async () => {
      const res = await profileApi.updateVendorDetails(data)
      setVendorProfile(res.data)
      // Sync contact_name → full_name so navbar/sidebar update immediately
      if (data.contact_name && user) {
        updateUser({ ...user, full_name: data.contact_name })
      }
      toast.success('Company profile updated')
    })
  }

  const handleInfoSubmit = infoForm.handleSubmit(data =>
    ask('Update Profile', 'Save these profile changes?', () => onInfoSave(data)))

  const handlePwSubmit = pwForm.handleSubmit(data => {
    if (data.new_password !== data.confirm_password) { toast.error('Passwords do not match'); return }
    ask('Change Password', 'Are you sure you want to change your password? You will stay logged in.', () => onPasswordSave(data))
  })

  const handleEmailSubmit = emailForm.handleSubmit(data =>
    ask('Change Email', `Change your login email to "${data.new_email}"?`, () => onEmailSave(data)))

  const handleVendorSubmit = vendorForm.handleSubmit(data =>
    ask('Update Company Profile', 'Save changes to your company profile?', () => onVendorSave(data)))

  const TABS = [
    { key: 'info',    label: 'Personal Info',    icon: <User size={15}/> },
    { key: 'security',label: 'Security',          icon: <Lock size={15}/> },
    ...(user?.role === 'vendor' ? [{ key: 'vendor', label: 'Company Profile', icon: <Building2 size={15}/> }] : []),
  ]

  const roleBadge: Record<string, string> = {
    admin: 'bg-purple-100 text-purple-700', manager: 'bg-blue-100 text-blue-700',
    vendor: 'bg-amber-100 text-amber-700', auditor: 'bg-gray-100 text-gray-700',
  }

  const Err = ({ form, field }: { form: any; field: string }) =>
    form.formState.errors[field]
      ? <p className="mt-1 text-xs text-red-500">{form.formState.errors[field].message as string}</p>
      : null

  return (
    <div className="max-w-3xl">
      <SectionHeader title="My Profile" description="Manage your account settings and preferences"/>

      {/* Profile header */}
      <div className="card p-6 mb-6 flex items-center gap-5">
        <div className="w-16 h-16 rounded-2xl bg-brand-600 flex items-center justify-center flex-shrink-0">
          <span className="text-2xl font-bold text-white">
            {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
          </span>
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-gray-900">{user?.full_name || 'No name set'}</h2>
          <p className="text-sm text-gray-500">{user?.email}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${roleBadge[user?.role || 'vendor']}`}>
              <ShieldCheck size={11}/> {user?.role?.charAt(0).toUpperCase()}{user?.role?.slice(1)}
            </span>
            {user?.region && user.region !== 'all' && (
              <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-50 text-brand-700">
                {REGION_LABELS[user.region] || user.region}
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-400">Member since</p>
          <p className="text-sm font-medium text-gray-700">
            {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }) : '—'}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 bg-gray-100 rounded-xl w-fit">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key as any)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              tab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Personal Info */}
      {tab === 'info' && (
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Personal Information</h3>
          <form onSubmit={handleInfoSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="label">Full Name *</label>
                <input {...infoForm.register('full_name', { required: 'Full name is required' })} className="input"/>
                <Err form={infoForm} field="full_name"/>
              </div>
              <div>
                <label className="label flex items-center gap-1"><Phone size={13}/> Phone</label>
                <input {...infoForm.register('phone', {
                  pattern: { value: /^[+]?[\d\s\-()]{8,15}$/, message: 'Enter a valid phone number' }
                })} className="input" placeholder="+91 98765 43210"/>
                <Err form={infoForm} field="phone"/>
              </div>
              <div>
                <label className="label">Designation</label>
                <input {...infoForm.register('designation')} className="input" placeholder="ESG Manager"/>
              </div>
            </div>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? <Spinner size="sm"/> : <><Save size={14}/> Save Changes</>}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Change Email Address</h3>
            <form onSubmit={handleEmailSubmit} className="space-y-3">
              <div>
                <label className="label">New Email Address *</label>
                <div className="relative">
                  <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
                  <input {...emailForm.register('new_email', { required: 'New email is required', pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email' } })}
                    type="email" className="input pl-9" placeholder="new@email.com"/>
                </div>
                <Err form={emailForm} field="new_email"/>
              </div>
              <div>
                <label className="label">Confirm with current password *</label>
                <input {...emailForm.register('current_password', { required: 'Password is required to confirm' })}
                  type="password" className="input" placeholder="••••••••"/>
                <Err form={emailForm} field="current_password"/>
              </div>
              <button type="submit" disabled={saving} className="btn-secondary">
                {saving ? <Spinner size="sm"/> : <><Mail size={14}/> Update Email</>}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Security */}
      {tab === 'security' && (
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Change Password</h3>
          <form onSubmit={handlePwSubmit} className="space-y-4 max-w-sm">
            <div>
              <label className="label">Current Password *</label>
              <input {...pwForm.register('current_password', { required: 'Current password is required' })}
                type="password" className="input" placeholder="••••••••"/>
              <Err form={pwForm} field="current_password"/>
            </div>
            <div>
              <label className="label">New Password *</label>
              <input {...pwForm.register('new_password', { required: 'New password is required', minLength: { value: 8, message: 'Min 8 characters' } })}
                type="password" className="input" placeholder="Min 8 characters"/>
              <Err form={pwForm} field="new_password"/>
            </div>
            <div>
              <label className="label">Confirm New Password *</label>
              <input {...pwForm.register('confirm_password', { required: 'Please confirm your password',
                validate: v => v === pwForm.watch('new_password') || 'Passwords do not match' })}
                type="password" className="input" placeholder="••••••••"/>
              <Err form={pwForm} field="confirm_password"/>
            </div>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? <Spinner size="sm"/> : <><Lock size={14}/> Change Password</>}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">Account Details</h3>
            <div className="space-y-2 text-sm">
              {[
                ['Role', user?.role],
                ['Region', user?.region && user.region !== 'all' ? REGION_LABELS[user.region] || user.region : 'Global'],
                ['Account Status', user?.is_active ? 'Active' : 'Inactive'],
                ['Onboarding', user?.onboarding_complete ? 'Complete' : 'Pending'],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between py-1.5 border-b border-gray-50">
                  <span className="text-gray-500">{label}</span>
                  <span className="font-medium text-gray-800 capitalize">{value as string}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Vendor Company Profile */}
      {tab === 'vendor' && vendorProfile && (
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Company Profile</h3>
          <form onSubmit={handleVendorSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Company Name *</label>
                <input {...vendorForm.register('company_name', { required: 'Required' })} className="input"/>
                <Err form={vendorForm} field="company_name"/>
              </div>
              <div><label className="label">Trade Name</label><input {...vendorForm.register('trade_name')} className="input"/></div>
              <div>
                <label className="label">GST Number *</label>
                <input {...vendorForm.register('gst_number', {
                  required: 'Required',
                  pattern: { value: /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/, message: 'Invalid GST format' }
                })} className="input"/>
                <Err form={vendorForm} field="gst_number"/>
              </div>
              <div>
                <label className="label">PAN Number *</label>
                <input {...vendorForm.register('pan_number', {
                  required: 'Required',
                  pattern: { value: /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/, message: 'Invalid PAN format' }
                })} className="input"/>
                <Err form={vendorForm} field="pan_number"/>
              </div>
              <div><label className="label">State</label><input {...vendorForm.register('state')} className="input"/></div>
              <div><label className="label">City</label><input {...vendorForm.register('city')} className="input"/></div>
              <div><label className="label">PIN Code</label><input {...vendorForm.register('pin_code', {
                pattern: { value: /^\d{6}$/, message: 'Must be 6 digits' }
              })} className="input" maxLength={6}/><Err form={vendorForm} field="pin_code"/></div>
              <div className="col-span-2">
                <label className="label">Address *</label>
                <textarea {...vendorForm.register('address', { required: 'Address is required' })} className="input" rows={2}/>
                <Err form={vendorForm} field="address"/>
              </div>
              <div>
                <label className="label">Contact Name *</label>
                <input {...vendorForm.register('contact_name', { required: 'Required' })} className="input"/>
                <Err form={vendorForm} field="contact_name"/>
              </div>
              <div>
                <label className="label">Contact Phone *</label>
                <input {...vendorForm.register('contact_phone', {
                  required: 'Required',
                  pattern: { value: /^[+]?[\d\s\-()]{8,15}$/, message: 'Invalid phone number' }
                })} className="input"/>
                <Err form={vendorForm} field="contact_phone"/>
              </div>
              <div className="col-span-2 flex items-center gap-3 pt-1">
                <input {...vendorForm.register('has_own_carbon_system')} type="checkbox" id="carbon_sys" className="w-4 h-4 accent-brand-600"/>
                <label htmlFor="carbon_sys" className="text-sm text-gray-700">We have our own carbon accounting system</label>
              </div>
            </div>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? <Spinner size="sm"/> : <><Save size={14}/> Save Company Profile</>}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide text-xs mb-3">Classification (contact manager to change)</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                ['Primary Category', vendorProfile.material_category ? `${vendorProfile.material_category}. ${SCOPE3_CATEGORIES[vendorProfile.material_category]}` : '—'],
                ['Material / Service', vendorProfile.material_name || '—'],
                ['NIC Code', vendorProfile.nic_code || '—'],
                ['Region', vendorProfile.region ? REGION_LABELS[vendorProfile.region] || vendorProfile.region : '—'],
              ].map(([label, value]) => (
                <div key={label as string} className="p-3 bg-gray-50 rounded-xl">
                  <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                  <p className="text-sm font-medium text-gray-800">{value as string}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog {...confirm} onCancel={closeConfirm}/>
    </div>
  )
}
