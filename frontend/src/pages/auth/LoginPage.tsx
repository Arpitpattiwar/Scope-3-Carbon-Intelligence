import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { ShieldCheck, Eye, EyeOff } from 'lucide-react'
import { authApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { Spinner } from '@/components/ui'

interface FormData { email: string; password: string }

export default function LoginPage() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>()
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      const res = await authApi.login(data.email, data.password)
      const { access_token, user } = res.data
      setAuth(user, access_token)

      if (user.must_change_password) {
        navigate('/change-password')
      } else if (!user.onboarding_complete && user.role === 'vendor') {
        navigate('/onboarding')
      } else {
        navigate('/dashboard')
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-brand-600 flex items-center justify-center shadow-lg shadow-brand-200 mb-3">
            <ShieldCheck size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">ESG Platform</h1>
          <p className="text-sm text-gray-500 mt-1">Scope 3 Carbon Intelligence</p>
        </div>

        {/* Form */}
        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-5">Sign in to your account</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Email address</label>
              <input
                {...register('email', { required: 'Email is required' })}
                type="email"
                placeholder="you@company.com"
                className="input"
              />
              {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  {...register('password', { required: 'Password is required' })}
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="input pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>}
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-2.5 mt-2">
              {loading ? <Spinner size="sm" /> : 'Sign in'}
            </button>
          </form>
        </div>

        {/* Demo credentials */}
        <div className="mt-4 p-4 bg-amber-50 border border-amber-100 rounded-xl">
          <p className="text-xs font-semibold text-amber-800 mb-2">Demo credentials</p>
          <div className="space-y-1 font-mono text-xs text-amber-700">
            <p>Admin: admin@stratxg.com / Admin@1234</p>
            <p>Manager (N): manager.north@stratxg.com / Manager@1234</p>
            <p>Manager (S): manager.south@stratxg.com / Manager@1234</p>
            <p>Vendor 1: vendor@acmesupplies.com / Vendor@1234</p>
            <p>Vendor 2: vendor@greentrans.com / Vendor@1234</p>
            <p>Vendor 3: vendor@wastecare.com / Vendor@1234</p>
            <p>Auditor: auditor@stratxg.com / Auditor@1234</p>
          </div>
        </div>
      </div>
    </div>
  )
}
