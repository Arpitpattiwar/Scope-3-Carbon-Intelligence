import { useEffect, useState } from 'react'
import { Plus, UserCheck, UserX, Trash2, Eye, X } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { usersApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { PageLoader, SectionHeader, Modal, Spinner } from '@/components/ui'
import { REGION_LABELS } from '@/utils/constants'
import clsx from 'clsx'

const ROLE_COLORS: Record<string, string> = {
  admin:   'bg-purple-100 text-purple-700',
  manager: 'bg-blue-100 text-blue-700',
  vendor:  'bg-amber-100 text-amber-700',
  auditor: 'bg-gray-100 text-gray-700',
}

// Hierarchy: admin can manage these roles
const MANAGEABLE_ROLES = ['manager', 'auditor']

export default function UsersPage() {
  const { user: currentUser } = useAuthStore()
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selectedUser, setSelectedUser] = useState<any>(null)
  const { register, handleSubmit, reset, formState: { errors } } = useForm()

  useEffect(() => { fetchUsers() }, [])

  const fetchUsers = async () => {
    setLoading(true)
    try { const res = await usersApi.list(); setUsers(res.data) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const onCreate = async (data: any) => {
    setSaving(true)
    try {
      await usersApi.create(data)
      toast.success('User created')
      setModalOpen(false); reset(); fetchUsers()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
    finally { setSaving(false) }
  }

  const toggleActive = async (id: number, current: boolean) => {
    if (id === currentUser?.id) { toast.error('Cannot deactivate your own account'); return }
    try {
      await usersApi.update(id, { is_active: !current })
      toast.success(current ? 'User deactivated' : 'User activated')
      fetchUsers()
      if (selectedUser?.id === id) setSelectedUser((u: any) => ({ ...u, is_active: !current }))
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  const deleteUser = async (id: number, email: string) => {
    if (id === currentUser?.id) { toast.error('Cannot delete your own account'); return }
    if (!confirm(`Deactivate user "${email}"? They will lose access but their data is preserved.`)) return
    try {
      await usersApi.delete(id)
      toast.success('User deactivated')
      fetchUsers()
      if (selectedUser?.id === id) setSelectedUser(null)
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
  }

  // Show non-vendor users (vendors managed in VendorsPage)
  const displayUsers = users.filter((u: any) => u.role !== 'vendor')

  return (
    <div className="flex gap-5">
      <div className={clsx('flex-1 min-w-0', selectedUser && 'lg:max-w-[calc(100%-300px)]')}>
        <SectionHeader title="User Management" description="Manage admins, managers, and auditors"
          action={<button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={16}/> New User</button>} />

        {loading ? <PageLoader /> : (
          <div className="card overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="table-header">Name / Email</th>
                  <th className="table-header">Role</th>
                  <th className="table-header">Region</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Created</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {displayUsers.map((u: any) => (
                  <tr key={u.id}
                    className={clsx('hover:bg-gray-50 transition-colors cursor-pointer',
                      selectedUser?.id === u.id && 'bg-brand-50')}
                    onClick={() => setSelectedUser(u)}>
                    <td className="table-cell">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                          <span className="text-xs font-semibold text-brand-700">
                            {u.full_name?.[0] || u.email?.[0] || '?'}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{u.full_name || '—'}</p>
                          <p className="text-xs text-gray-400">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[u.role] || 'bg-gray-100'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="table-cell text-sm capitalize">
                      {u.region && u.region !== 'all' ? REGION_LABELS[u.region] || u.region : 'All regions'}
                    </td>
                    <td className="table-cell">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="table-cell text-xs text-gray-500">
                      {new Date(u.created_at).toLocaleDateString('en-IN')}
                    </td>
                    <td className="table-cell" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        {u.id !== currentUser?.id && MANAGEABLE_ROLES.includes(u.role) && (
                          <>
                            <button onClick={() => toggleActive(u.id, u.is_active)}
                              className={`p-1.5 rounded-lg transition-colors ${u.is_active ? 'hover:bg-amber-50 text-amber-500' : 'hover:bg-green-50 text-green-600'}`}
                              title={u.is_active ? 'Deactivate' : 'Activate'}>
                              {u.is_active ? <UserX size={14}/> : <UserCheck size={14}/>}
                            </button>
                            <button onClick={() => deleteUser(u.id, u.email)}
                              className="p-1.5 hover:bg-red-50 text-red-400 rounded-lg transition-colors" title="Delete user">
                              <Trash2 size={14}/>
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
        )}
      </div>

      {/* User detail panel */}
      {selectedUser && (
        <div className="w-72 flex-shrink-0 hidden lg:block">
          <div className="card p-5 sticky top-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900">User Details</h3>
              <button onClick={() => setSelectedUser(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                <X size={15} className="text-gray-400"/>
              </button>
            </div>
            <div className="flex flex-col items-center mb-4">
              <div className="w-14 h-14 rounded-2xl bg-brand-100 flex items-center justify-center mb-2">
                <span className="text-xl font-bold text-brand-700">
                  {selectedUser.full_name?.[0] || selectedUser.email?.[0] || '?'}
                </span>
              </div>
              <p className="text-sm font-semibold text-gray-900">{selectedUser.full_name || 'No name'}</p>
              <p className="text-xs text-gray-400">{selectedUser.email}</p>
              <span className={`mt-2 inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[selectedUser.role]}`}>
                {selectedUser.role}
              </span>
            </div>
            <div className="space-y-2">
              {[
                ['Region', selectedUser.region && selectedUser.region !== 'all' ? REGION_LABELS[selectedUser.region] || selectedUser.region : 'All regions'],
                ['Phone', selectedUser.phone || '—'],
                ['Designation', selectedUser.designation || '—'],
                ['Status', selectedUser.is_active ? '🟢 Active' : '🔴 Inactive'],
                ['Member since', new Date(selectedUser.created_at).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between text-xs py-1 border-b border-gray-50 last:border-0">
                  <span className="text-gray-400">{label}</span>
                  <span className="text-gray-800 font-medium">{value as string}</span>
                </div>
              ))}
            </div>
            {selectedUser.id !== currentUser?.id && MANAGEABLE_ROLES.includes(selectedUser.role) && (
              <div className="flex gap-2 mt-4">
                <button onClick={() => toggleActive(selectedUser.id, selectedUser.is_active)}
                  className={`flex-1 text-xs py-2 rounded-lg font-medium transition-colors ${selectedUser.is_active ? 'bg-amber-50 text-amber-700 hover:bg-amber-100' : 'bg-green-50 text-green-700 hover:bg-green-100'}`}>
                  {selectedUser.is_active ? 'Deactivate' : 'Activate'}
                </button>
                <button onClick={() => deleteUser(selectedUser.id, selectedUser.email)}
                  className="flex-1 text-xs py-2 rounded-lg font-medium bg-red-50 text-red-600 hover:bg-red-100 transition-colors">
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create user modal */}
      <Modal open={modalOpen} onClose={() => { setModalOpen(false); reset() }} title="Create User" size="sm">
        <form onSubmit={handleSubmit(onCreate)} className="space-y-4">
          <div>
            <label className="label">Full Name *</label>
            <input {...register('full_name', { required: 'Required' })} className="input" placeholder="Jane Doe"/>
            {errors.full_name && <p className="mt-1 text-xs text-red-500">{errors.full_name.message as string}</p>}
          </div>
          <div>
            <label className="label">Email *</label>
            <input {...register('email', { required: 'Required' })} type="email" className="input"/>
            {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message as string}</p>}
          </div>
          <div>
            <label className="label">Role *</label>
            <select {...register('role', { required: 'Required' })} className="input">
              <option value="">Select role</option>
              <option value="manager">Manager</option>
              <option value="auditor">Auditor</option>
              <option value="admin">Admin</option>
            </select>
            {errors.role && <p className="mt-1 text-xs text-red-500">{errors.role.message as string}</p>}
          </div>
          <div>
            <label className="label">Region (for managers)</label>
            <select {...register('region')} className="input">
              <option value="">None (admin / auditor)</option>
              {['north','south','east','west','central'].map(r => (
                <option key={r} value={r}>{REGION_LABELS[r]}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Password *</label>
            <input {...register('password', { required: 'Required', minLength: { value: 8, message: 'Min 8 characters' } })} type="password" className="input" placeholder="Min 8 characters"/>
            {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message as string}</p>}
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => { setModalOpen(false); reset() }} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
              {saving ? <Spinner size="sm"/> : 'Create User'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
