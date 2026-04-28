export const SCOPE3_CATEGORIES: Record<number, string> = {
  1: 'Purchased Goods & Services',
  2: 'Capital Goods',
  3: 'Fuel & Energy Related Activities',
  4: 'Upstream Transport & Distribution',
  5: 'Waste Generated in Operations',
  6: 'Business Travel',
  7: 'Employee Commuting',
  8: 'Downstream Transport & Distribution',
  9: 'Processing of Sold Products',
  10: 'Use of Sold Products',
  11: 'End-of-Life Treatment',
  12: 'Leased Assets',
  13: 'Franchises',
  14: 'Investments',
  15: 'Other (Custom)',
}

export const REGIONS = ['north', 'south', 'east', 'west', 'central'] as const
export type Region = typeof REGIONS[number]

export const REGION_LABELS: Record<string, string> = {
  north: 'North India',
  south: 'South India',
  east: 'East India',
  west: 'West India',
  central: 'Central India',
}

export const CHART_COLORS = [
  '#1aa876', '#0f8660', '#38c28d', '#6dd9ad',
  '#0d553f', '#a5eacb', '#2563eb', '#7c3aed',
  '#dc2626', '#d97706', '#0891b2', '#65a30d',
  '#9333ea', '#db2777', '#ea580c',
]

export const DATA_QUALITY_LABELS: Record<string, string> = {
  A: 'Primary Data',
  B: 'Proxy/Benchmark',
  C: 'AI Estimated',
}

export function formatCO2e(value: number): string {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k tCO₂e`
  if (value < 0.01) return `${(value * 1000).toFixed(2)} kgCO₂e`
  return `${value.toFixed(2)} tCO₂e`
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
