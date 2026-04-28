import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { efApi } from '@/utils/api'
import { PageLoader, SectionHeader, Modal, EmptyState, Spinner, Select } from '@/components/ui'
import { SCOPE3_CATEGORIES } from '@/utils/constants'

export default function EFLibraryPage() {
  const [efs, setEfs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [catFilter, setCatFilter] = useState('')
  const { register, handleSubmit, reset } = useForm()

  useEffect(() => { fetchEFs() }, [catFilter])

  const fetchEFs = async () => {
    setLoading(true)
    try {
      const res = await efApi.list(catFilter ? { category_id: parseInt(catFilter) } : {})
      setEfs(res.data)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const onCreate = async (data: any) => {
    setSaving(true)
    try {
      await efApi.create({ ...data, category_id: parseInt(data.category_id), factor_value: parseFloat(data.factor_value) })
      toast.success('Emission factor added')
      setModalOpen(false); reset(); fetchEFs()
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Failed') }
    finally { setSaving(false) }
  }

  const onDeactivate = async (id: number) => {
    if (!confirm('Deactivate this emission factor?')) return
    try {
      await efApi.deactivate(id)
      toast.success('Factor deactivated')
      fetchEFs()
    } catch { toast.error('Failed') }
  }

  const catOptions = [{ value: '', label: 'All Categories' }, ...Object.entries(SCOPE3_CATEGORIES).map(([id, name]) => ({ value: id, label: `${id}. ${name}` }))]
  const sourceColors: Record<string, string> = { DEFRA: 'bg-blue-100 text-blue-700', IPCC: 'bg-purple-100 text-purple-700', CPCB: 'bg-green-100 text-green-700', custom: 'bg-gray-100 text-gray-700' }

  return (
    <div>
      <SectionHeader title="Emission Factor Library" description="DEFRA, IPCC, and CPCB emission factors used in calculations"
        action={<button onClick={() => setModalOpen(true)} className="btn-primary"><Plus size={16} /> Add Factor</button>} />

      <div className="mb-4">
        <Select options={catOptions} value={catFilter} onChange={setCatFilter} className="w-64" />
      </div>

      {loading ? <PageLoader /> : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="table-header">Category</th>
                <th className="table-header">Material / Type</th>
                <th className="table-header">Factor Value</th>
                <th className="table-header">Unit</th>
                <th className="table-header">Source</th>
                <th className="table-header">Version</th>
                <th className="table-header">Region</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {efs.map((ef: any) => (
                <tr key={ef.id} className="hover:bg-gray-50 transition-colors">
                  <td className="table-cell"><span className="text-xs font-medium text-gray-500">Cat {ef.category_id}</span></td>
                  <td className="table-cell">
                    <p className="font-medium text-sm">{ef.material_type || ef.subcategory || '—'}</p>
                    {ef.subcategory && ef.material_type && <p className="text-xs text-gray-400">{ef.subcategory}</p>}
                  </td>
                  <td className="table-cell font-mono font-semibold text-brand-700">{ef.factor_value}</td>
                  <td className="table-cell text-xs font-mono text-gray-500">{ef.unit}</td>
                  <td className="table-cell"><span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${sourceColors[ef.source] || 'bg-gray-100'}`}>{ef.source}</span></td>
                  <td className="table-cell text-xs text-gray-500">{ef.version_tag}</td>
                  <td className="table-cell text-xs text-gray-500 capitalize">{ef.region || 'global'}</td>
                  <td className="table-cell">
                    <button onClick={() => onDeactivate(ef.id)} className="p-1.5 hover:bg-red-50 text-red-400 rounded-lg transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => { setModalOpen(false); reset() }} title="Add Emission Factor" size="md">
        <form onSubmit={handleSubmit(onCreate)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Category *</label>
              <select {...register('category_id', { required: true })} className="input">
                <option value="">Select</option>
                {Object.entries(SCOPE3_CATEGORIES).map(([id, name]) => <option key={id} value={id}>{id}. {name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Source *</label>
              <select {...register('source', { required: true })} className="input">
                <option value="DEFRA">DEFRA</option>
                <option value="IPCC">IPCC</option>
                <option value="CPCB">CPCB</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div><label className="label">Subcategory</label><input {...register('subcategory')} className="input" /></div>
            <div><label className="label">Material Type</label><input {...register('material_type')} className="input" /></div>
            <div>
              <label className="label">Factor Value *</label>
              <input {...register('factor_value', { required: true })} type="number" step="any" className="input" />
            </div>
            <div><label className="label">Unit *</label><input {...register('unit', { required: true })} className="input" placeholder="kgCO2e/tonne" /></div>
            <div><label className="label">Region</label><input {...register('region')} className="input" defaultValue="global" /></div>
            <div><label className="label">Version Tag *</label><input {...register('version_tag', { required: true })} className="input" placeholder="DEFRA_2024_v1" /></div>
            <div className="col-span-2"><label className="label">Source URL</label><input {...register('source_url')} className="input" /></div>
            <div className="col-span-2"><label className="label">Notes</label><textarea {...register('notes')} className="input" rows={2} /></div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => { setModalOpen(false); reset() }} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 justify-center">
              {saving ? <Spinner size="sm" /> : 'Add Factor'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
