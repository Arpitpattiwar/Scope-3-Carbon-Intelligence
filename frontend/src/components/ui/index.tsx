import React from 'react'
import { Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'

// ── Loading spinner ───────────────────────────────────────────────────────────
export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }
  return <Loader2 className={clsx('animate-spin text-brand-600', sizes[size])} />
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <Spinner size="lg" />
    </div>
  )
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
interface KpiCardProps {
  label: string
  value: string | number
  unit?: string
  change?: number | null
  changeLabel?: string
  icon?: React.ReactNode
  color?: string
  tooltip?: string
}

export function KpiCard({ label, value, unit, change, changeLabel, icon, color = 'brand' }: KpiCardProps) {
  return (
    <div className="kpi-card">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</p>
        {icon && (
          <div className={`p-2 rounded-xl bg-${color}-50 text-${color}-600`}>
            {icon}
          </div>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-2xl font-semibold text-gray-900">{value}</span>
        {unit && <span className="text-sm text-gray-500">{unit}</span>}
      </div>
      {change !== undefined && change !== null && (
        <div className="mt-1 flex items-center gap-1">
          {change > 0 ? (
            <TrendingUp className="w-3 h-3 text-red-500" />
          ) : change < 0 ? (
            <TrendingDown className="w-3 h-3 text-green-500" />
          ) : (
            <Minus className="w-3 h-3 text-gray-400" />
          )}
          <span className={clsx('text-xs font-medium', 
            change > 0 ? 'text-red-600' : change < 0 ? 'text-green-600' : 'text-gray-500'
          )}>
            {change > 0 ? '+' : ''}{change}% {changeLabel || 'vs last year'}
          </span>
        </div>
      )}
    </div>
  )
}

// ── Data quality badge ────────────────────────────────────────────────────────
export function QualityBadge({ quality }: { quality: string }) {
  return (
    <span className={`badge-${quality}`}>
      {quality === 'A' ? '🟢 A — Primary' : quality === 'B' ? '🟡 B — Proxy' : '🔴 C — Estimated'}
    </span>
  )
}

// ── Status badge ──────────────────────────────────────────────────────────────
export function StatusBadge({ status }: { status: string }) {
  return <span className={`status-${status}`}>{status}</span>
}

// ── Empty state ───────────────────────────────────────────────────────────────
export function EmptyState({ title, description, action }: {
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
        <span className="text-2xl">📭</span>
      </div>
      <h3 className="text-sm font-semibold text-gray-900 mb-1">{title}</h3>
      {description && <p className="text-sm text-gray-500 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// ── Modal ────────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, size = 'md' }: {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}) {
  if (!open) return null
  const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className={clsx('relative bg-white rounded-2xl shadow-2xl w-full', widths[size])}>
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <svg className="w-4 h-4 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" />
            </svg>
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

// ── Select dropdown ───────────────────────────────────────────────────────────
export function Select({ options, value, onChange, placeholder, className }: {
  options: { value: string; label: string }[]
  value: string
  onChange: (v: string) => void
  placeholder?: string
  className?: string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={clsx('input', className)}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

// ── Section header ────────────────────────────────────────────────────────────
export function SectionHeader({ title, description, action }: {
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
