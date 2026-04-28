import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { CHART_COLORS } from '@/utils/constants'

const TT = { borderRadius: '12px', border: '1px solid #e5e7eb', boxShadow: '0 4px 24px rgba(0,0,0,0.08)', fontSize: '13px' }

export function TrendChart({ data }: { data: { period: string; total_co2e: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="co2eGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#1aa876" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#1aa876" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
        <Tooltip contentStyle={TT} formatter={(v: number) => [`${v.toFixed(2)} tCO₂e`, 'Emissions']} />
        <Area type="monotone" dataKey="total_co2e" stroke="#1aa876" strokeWidth={2} fill="url(#co2eGrad)" dot={{ r: 3, fill: '#1aa876' }} activeDot={{ r: 5 }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function CategoryBarChart({ data }: { data: { category_id: number; category_name: string; total_co2e: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data.slice(0, 8)} layout="vertical" margin={{ top: 0, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="category_name" tick={{ fontSize: 11, fill: '#6b7280' }} axisLine={false} tickLine={false} width={170} tickFormatter={v => v.length > 26 ? v.slice(0, 24) + '…' : v} />
        <Tooltip contentStyle={TT} formatter={(v: number) => [`${v.toFixed(3)} tCO₂e`, 'Emissions']} />
        <Bar dataKey="total_co2e" radius={[0, 6, 6, 0]} maxBarSize={22}>
          {data.slice(0, 8).map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function RegionDonutChart({ data }: { data: { region: string; total_co2e: number }[] }) {
  const C = ['#1aa876', '#0f8660', '#38c28d', '#6dd9ad', '#0d553f']
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="total_co2e" nameKey="region" paddingAngle={3}>
          {data.map((_, i) => <Cell key={i} fill={C[i % C.length]} />)}
        </Pie>
        <Tooltip contentStyle={TT} formatter={(v: number) => [`${v.toFixed(2)} tCO₂e`, '']} />
        <Legend formatter={v => <span style={{ fontSize: 11, textTransform: 'capitalize' }}>{v}</span>} />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function VendorBarChart({ data }: { data: { company_name: string; total_co2e: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data.slice(0, 8)} margin={{ top: 5, right: 10, left: 0, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis dataKey="company_name" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} angle={-30} textAnchor="end" tickFormatter={v => v.length > 12 ? v.slice(0, 10) + '…' : v} />
        <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={TT} formatter={(v: number) => [`${v.toFixed(2)} tCO₂e`, 'Emissions']} />
        <Bar dataKey="total_co2e" radius={[6, 6, 0, 0]} maxBarSize={40}>
          {data.slice(0, 8).map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function Sparkline({ data, color = '#1aa876' }: { data: number[]; color?: string }) {
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data.map((v, i) => ({ v, i }))}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
