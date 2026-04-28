import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { CheckCircle2, ChevronRight, ChevronLeft, ShieldCheck, Loader2 } from 'lucide-react'
import { usersApi } from '@/utils/api'
import { useAuthStore } from '@/store/authStore'
import { Spinner } from '@/components/ui'
import { SCOPE3_CATEGORIES } from '@/utils/constants'
import {
  getStatesForRegion, getCitiesForState, getPincodeForCity, verifyPincode
} from '@/utils/indiaGeo'

const STEPS = ['Company Info', 'Location', 'Operations', 'Contact']

const VOLUME_UNITS = [
  'tonnes', 'kg', 'litres', 'kL (kilolitres)', 'kWh', 'MWh',
  'km', 'tonne-km', 'passenger-km', 'vehicle-km',
  'units', 'pieces', 'INR (spend-based)', 'USD (spend-based)',
  'Custom (specify below)',
]

const currentYear = new Date().getFullYear()
const YEARS = Array.from({ length: currentYear - 1500 + 51 }, (_, i) => currentYear + 50 - i)

export default function OnboardingPage() {
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [cities, setCities] = useState<string[]>([])
  const [pincodeChecking, setPincodeChecking] = useState(false)
  const [pincodeStatus, setPincodeStatus] = useState<'ok' | 'error' | null>(null)
  const { user, updateUser } = useAuthStore()
  const navigate = useNavigate()

  const {
    register, handleSubmit, watch, setValue,
    formState: { errors }, trigger,
  } = useForm({ mode: 'onBlur' })

  const watchState = watch('state')
  const watchCity  = watch('city')
  const watchPin   = watch('pin_code')
  const watchUnit  = watch('volume_unit')

  const userRegion = user?.region || ''

  // Populate cities when state changes
  useEffect(() => {
    if (watchState) {
      const c = getCitiesForState(watchState)
      setCities(c)
      setValue('city', '')
      setValue('pin_code', '')
      setPincodeStatus(null)
    }
  }, [watchState])

  // Prepopulate pincode when city changes
  useEffect(() => {
    if (watchCity) {
      const pin = getPincodeForCity(watchCity)
      if (pin) { setValue('pin_code', pin); setPincodeStatus(null) }
    }
  }, [watchCity])

  // Verify pincode when it changes (debounced)
  useEffect(() => {
    if (!watchPin || watchPin.length !== 6) { setPincodeStatus(null); return }
    const t = setTimeout(async () => {
      setPincodeChecking(true)
      const result = await verifyPincode(watchPin)
      setPincodeStatus(result.valid ? 'ok' : 'error')
      if (!result.valid && result.error) toast.error(result.error)
      setPincodeChecking(false)
    }, 800)
    return () => clearTimeout(t)
  }, [watchPin])

  const stepFields: Record<number, string[]> = {
    0: ['company_name', 'gst_number', 'pan_number', 'nic_code', 'year_established'],
    1: ['state', 'city', 'pin_code', 'address'],
    2: ['material_category', 'material_name', 'supply_frequency'],
    3: ['contact_name', 'contact_phone', 'declaration'],
  }

  const nextStep = async () => {
    const valid = await trigger(stepFields[step] as any)
    if (!valid) return
    // Block on Location step if pincode is being checked or is invalid
    if (step === 1) {
      if (pincodeChecking) { toast.error('Please wait — verifying pincode...'); return }
      if (pincodeStatus === 'error') {
        toast.error('Invalid PIN code — please enter a valid 6-digit Indian postal code')
        return
      }
    }
    setStep(s => s + 1)
  }

  const onSubmit = async (data: any) => {
    setLoading(true)
    try {
      const unit = data.volume_unit === 'Custom (specify below)'
        ? data.custom_volume_unit
        : data.volume_unit

      await usersApi.onboard({
        ...data,
        material_category: parseInt(data.material_category),
        avg_annual_volume: data.avg_annual_volume ? parseFloat(data.avg_annual_volume) : undefined,
        year_established: data.year_established ? parseInt(data.year_established) : undefined,
        has_own_carbon_system: !!data.has_own_carbon_system,
        volume_unit: unit,
      })
      if (user) updateUser({ ...user, onboarding_complete: true, full_name: data.contact_name })
      toast.success('Onboarding complete! Your profile is ready.')
      navigate('/dashboard')
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Onboarding failed')
    } finally { setLoading(false) }
  }

  const states = getStatesForRegion(userRegion)

  const Err = ({ field }: { field: string }) =>
    errors[field] ? <p className="mt-1 text-xs text-red-500">{errors[field]!.message as string}</p> : null

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center">
            <ShieldCheck size={20} className="text-white"/>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Welcome to the Platform</h1>
            <p className="text-sm text-gray-500">Complete your vendor profile to start submitting data</p>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex items-center gap-0 mb-6">
          {STEPS.map((label, i) => (
            <div key={i} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold transition-all ${
                  i < step ? 'bg-brand-600 text-white' :
                  i === step ? 'bg-brand-600 text-white ring-4 ring-brand-100' :
                  'bg-gray-100 text-gray-400'
                }`}>
                  {i < step ? <CheckCircle2 size={14}/> : i + 1}
                </div>
                <span className={`text-xs mt-1 font-medium ${i === step ? 'text-brand-700' : 'text-gray-400'}`}>{label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-px mb-4 mx-2 ${i < step ? 'bg-brand-300' : 'bg-gray-200'}`}/>
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="card p-6 min-h-[400px]">

            {/* ── Step 0: Company Info ── */}
            {step === 0 && (
              <div className="space-y-4">
                <h2 className="text-base font-semibold text-gray-900 mb-1">Company Information</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="label">Legal Company Name *</label>
                    <input {...register('company_name', { required: 'Company name is required' })}
                      className="input" placeholder="Acme Supplies Pvt Ltd"/>
                    <Err field="company_name"/>
                  </div>
                  <div>
                    <label className="label">Trade Name</label>
                    <input {...register('trade_name')} className="input" placeholder="Optional"/>
                  </div>
                  <div>
                    <label className="label">Year Established *</label>
                    <select {...register('year_established', { required: 'Year established is required' })} className="input">
                      <option value="">Select year</option>
                      {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                    </select>
                    <Err field="year_established"/>
                  </div>
                  <div>
                    <label className="label">GST Number *
                      <span className="ml-1 text-xs text-gray-400 font-normal">(15 chars: 27AABCA1234B1Z5)</span>
                    </label>
                    <input {...register('gst_number', {
                      required: 'GST number is required',
                      pattern: { value: /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/,
                        message: 'Invalid GST format (e.g. 27AABCA1234B1Z5)' }
                    })} className="input" placeholder="27AABCA1234B1Z5" maxLength={15}/>
                    <Err field="gst_number"/>
                  </div>
                  <div>
                    <label className="label">PAN Number *
                      <span className="ml-1 text-xs text-gray-400 font-normal">(10 chars: AABCA1234B)</span>
                    </label>
                    <input {...register('pan_number', {
                      required: 'PAN number is required',
                      pattern: { value: /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/,
                        message: 'Invalid PAN format (e.g. AABCA1234B)' }
                    })} className="input" placeholder="AABCA1234B" maxLength={10}
                      onChange={e => setValue('pan_number', e.target.value.toUpperCase())}/>
                    <Err field="pan_number"/>
                  </div>
                  <div>
                    <label className="label">CIN Number
                      <span className="ml-1 text-xs text-gray-400 font-normal">(optional)</span>
                    </label>
                    <input {...register('cin_number', {
                      pattern: { value: /^[UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$/,
                        message: 'Invalid CIN format' }
                    })} className="input" placeholder="U74999MH2010PTC123456"/>
                    <Err field="cin_number"/>
                  </div>
                  <div>
                    <label className="label">NIC Industry Code *
                      <span className="ml-1 text-xs text-gray-400 font-normal">(4–5 digits)</span>
                    </label>
                    <input {...register('nic_code', {
                      required: 'NIC code is required',
                      pattern: { value: /^[0-9]{4,5}$/, message: 'NIC code must be 4–5 digits' }
                    })} className="input" placeholder="46610" maxLength={5}/>
                    <Err field="nic_code"/>
                    <p className="text-xs text-gray-400 mt-1">
                      Find yours at{' '}
                      <a href="https://mospi.gov.in/sites/default/files/main-menu/nec-nic/NIC2008_17Apr09.pdf"
                        target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline">
                        mospi.gov.in →
                      </a>
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* ── Step 1: Location ── */}
            {step === 1 && (
              <div className="space-y-4">
                <h2 className="text-base font-semibold text-gray-900 mb-1">Location Details</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">State *</label>
                    <select {...register('state', { required: 'State is required' })} className="input">
                      <option value="">Select state</option>
                      {states.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <Err field="state"/>
                  </div>
                  <div>
                    <label className="label">City *</label>
                    <select {...register('city', { required: 'City is required' })} className="input"
                      disabled={!watchState || cities.length === 0}>
                      <option value="">Select city</option>
                      {cities.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <Err field="city"/>
                    {watchState && cities.length === 0 && (
                      <p className="text-xs text-amber-600 mt-1">No cities listed — please enter manually below</p>
                    )}
                  </div>
                  <div>
                    <label className="label flex items-center gap-1">
                      PIN Code *
                      {pincodeChecking && <Loader2 size={12} className="animate-spin text-gray-400"/>}
                      {pincodeStatus === 'ok' && <CheckCircle2 size={12} className="text-green-500"/>}
                      {pincodeStatus === 'error' && <span className="text-xs text-red-500">⚠ Not found</span>}
                    </label>
                    <input {...register('pin_code', {
                      required: 'PIN code is required',
                      pattern: { value: /^\d{6}$/, message: 'Must be exactly 6 digits' }
                    })} className="input" placeholder="400001" maxLength={6}/>
                    <Err field="pin_code"/>
                  </div>
                  <div className="col-span-2">
                    <label className="label">Full Address *</label>
                    <textarea {...register('address', { required: 'Address is required' })}
                      className="input" rows={3}
                      placeholder="Plot 12, MIDC Industrial Area, Andheri East..."/>
                    <Err field="address"/>
                  </div>
                </div>
              </div>
            )}

            {/* ── Step 2: Operations ── */}
            {step === 2 && (
              <div className="space-y-4">
                <h2 className="text-base font-semibold text-gray-900 mb-1">Supply & Operations</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="label">Primary Scope 3 Category *</label>
                    <select {...register('material_category', { required: 'Please select a category' })} className="input">
                      <option value="">Select category</option>
                      {Object.entries(SCOPE3_CATEGORIES).map(([id, name]) => (
                        <option key={id} value={id}>{id}. {name}</option>
                      ))}
                    </select>
                    <Err field="material_category"/>
                  </div>
                  <div className="col-span-2">
                    <label className="label">Material / Service Name *</label>
                    <input {...register('material_name', { required: 'Required' })}
                      className="input" placeholder="e.g. Cold-rolled steel sheets"/>
                    <Err field="material_name"/>
                  </div>
                  <div>
                    <label className="label">Supply Frequency *</label>
                    <select {...register('supply_frequency', { required: 'Required' })} className="input">
                      <option value="">Select</option>
                      {['weekly','monthly','quarterly','annually','on-demand'].map(v => (
                        <option key={v} value={v}>{v.charAt(0).toUpperCase()+v.slice(1)}</option>
                      ))}
                    </select>
                    <Err field="supply_frequency"/>
                  </div>
                  <div>
                    <label className="label">Avg. Annual Volume</label>
                    <input {...register('avg_annual_volume')} type="number" className="input" placeholder="5000"/>
                  </div>
                  <div>
                    <label className="label">Volume Unit</label>
                    <select {...register('volume_unit')} className="input">
                      <option value="">Select unit</option>
                      {VOLUME_UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </div>
                  {watchUnit === 'Custom (specify below)' && (
                    <div>
                      <label className="label">Custom Unit *</label>
                      <input {...register('custom_volume_unit', { required: watchUnit === 'Custom (specify below)' ? 'Required' : false })}
                        className="input" placeholder="e.g. metric tons, pallets"/>
                      <Err field="custom_volume_unit"/>
                    </div>
                  )}
                  <div className="flex items-center gap-3 col-span-2 pt-1">
                    <input {...register('has_own_carbon_system')} type="checkbox" id="carbon_sys"
                      className="w-4 h-4 rounded accent-brand-600"/>
                    <label htmlFor="carbon_sys" className="text-sm text-gray-700">
                      We have our own carbon accounting system
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* ── Step 3: Contact ── */}
            {step === 3 && (
              <div className="space-y-4">
                <h2 className="text-base font-semibold text-gray-900 mb-1">Primary Contact</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">Contact Name *</label>
                    <input {...register('contact_name', { required: 'Contact name is required' })}
                      className="input" placeholder="Rahul Sharma"/>
                    <Err field="contact_name"/>
                  </div>
                  <div>
                    <label className="label">Designation</label>
                    <input {...register('contact_designation')} className="input" placeholder="ESG Manager"/>
                  </div>
                  <div>
                    <label className="label">Phone Number *</label>
                    <input {...register('contact_phone', {
                      required: 'Phone number is required',
                      pattern: { value: /^[+]?[\d\s\-()]{8,15}$/, message: 'Enter a valid phone number' }
                    })} className="input" placeholder="+91 98765 43210"/>
                    <Err field="contact_phone"/>
                  </div>
                </div>

                <div className="mt-4 p-4 bg-brand-50 border border-brand-100 rounded-xl">
                  <p className="text-xs text-brand-800 leading-relaxed">
                    <strong>Declaration:</strong> I confirm that the emissions data submitted through
                    this platform will be accurate to the best of my knowledge, and I understand
                    that it will be used for GRI 305 / GHG Protocol Scope 3 reporting.
                  </p>
                  <div className="flex items-start gap-2 mt-3">
                    <input {...register('declaration', { required: 'You must accept the declaration to proceed' })}
                      type="checkbox" id="declaration" className="w-4 h-4 mt-0.5 rounded accent-brand-600"/>
                    <label htmlFor="declaration" className="text-sm text-brand-700 cursor-pointer">
                      I accept and confirm the above declaration *
                    </label>
                  </div>
                  <Err field="declaration"/>
                </div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-5">
            <button type="button" onClick={() => setStep(s => s - 1)} disabled={step === 0}
              className="btn-secondary disabled:opacity-40">
              <ChevronLeft size={16}/> Back
            </button>
            {step < STEPS.length - 1 ? (
              <button type="button" onClick={nextStep} className="btn-primary">
                Continue <ChevronRight size={16}/>
              </button>
            ) : (
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? <Spinner size="sm"/> : <><CheckCircle2 size={16}/> Complete Setup</>}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
