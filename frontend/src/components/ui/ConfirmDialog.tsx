import { AlertTriangle } from 'lucide-react'

interface Props {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'warning' | 'info'
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  open, title, message,
  confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  variant = 'warning',
  onConfirm, onCancel,
}: Props) {
  if (!open) return null

  const colors = {
    danger:  { icon: 'text-red-500',    btn: 'btn-danger',   bg: 'bg-red-50 border-red-100' },
    warning: { icon: 'text-amber-500',  btn: 'btn-primary',  bg: 'bg-amber-50 border-amber-100' },
    info:    { icon: 'text-brand-500',  btn: 'btn-primary',  bg: 'bg-brand-50 border-brand-100' },
  }
  const c = colors[variant]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onCancel}/>
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <div className={`flex items-start gap-3 p-4 rounded-xl border mb-4 ${c.bg}`}>
          <AlertTriangle size={18} className={`${c.icon} flex-shrink-0 mt-0.5`}/>
          <div>
            <p className="text-sm font-semibold text-gray-900">{title}</p>
            <p className="text-xs text-gray-600 mt-1">{message}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={onCancel} className="btn-secondary flex-1 justify-center">{cancelLabel}</button>
          <button onClick={onConfirm} className={`${c.btn} flex-1 justify-center`}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
