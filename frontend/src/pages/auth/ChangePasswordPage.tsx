import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { KeyRound } from 'lucide-react'
import { profileApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { Spinner } from '@/components/ui'

interface FormData { current_password: string; new_password: string; confirm: string }

export default function ChangePasswordPage() {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>()
  const [loading, setLoading] = useState(false)
  const { user, updateUser } = useAuthStore()
  const navigate = useNavigate()

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      await profileApi.changePassword({ current_password: data.current_password, new_password: data.new_password })
      toast.success('Password changed successfully')
      if (user) updateUser({ ...user, must_change_password: false })
      if (user?.role === 'vendor' && !user.onboarding_complete) {
        navigate('/onboarding')
      } else {
        navigate('/dashboard')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-brand-600 flex items-center justify-center shadow-lg shadow-brand-200 mb-3">
            <KeyRound size={24} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">Set a new password</h1>
          <p className="text-sm text-gray-500 mt-1">You need to change your temporary password before continuing.</p>
        </div>
        <div className="card p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Current / temporary password</label>
              <input {...register('current_password', { required: true })} type="password" className="input" />
            </div>
            <div>
              <label className="label">New password</label>
              <input {...register('new_password', { required: true, minLength: { value: 8, message: 'Min 8 characters' } })} type="password" className="input" />
              {errors.new_password && <p className="mt-1 text-xs text-red-500">{errors.new_password.message}</p>}
            </div>
            <div>
              <label className="label">Confirm new password</label>
              <input {...register('confirm', { validate: v => v === watch('new_password') || 'Passwords do not match' })} type="password" className="input" />
              {errors.confirm && <p className="mt-1 text-xs text-red-500">{errors.confirm.message}</p>}
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-2.5 mt-2">
              {loading ? <Spinner size="sm" /> : 'Set new password & continue'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
