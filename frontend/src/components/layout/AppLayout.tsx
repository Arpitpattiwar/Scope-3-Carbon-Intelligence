import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import {
  LayoutDashboard, Factory, Users, FileText, Settings,
  LogOut, ClipboardCheck, BarChart3, Upload, ShieldCheck,
  Building2, UserCircle, History, Calculator, Bell
} from 'lucide-react'
import clsx from 'clsx'
import NotificationBell from './NotificationBell'

interface NavItem { to: string; label: string; icon: React.ReactNode; roles: string[] }

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard',          label: 'Dashboard',          icon: <LayoutDashboard size={18}/>, roles: ['admin','manager','vendor','auditor'] },
  { to: '/emissions',          label: 'Emission Records',   icon: <Factory size={18}/>,         roles: ['admin','manager','vendor','auditor'] },
  { to: '/submit',             label: 'Submit Data',        icon: <Upload size={18}/>,          roles: ['vendor'] },
  { to: '/history',            label: 'My History',         icon: <History size={18}/>,         roles: ['vendor'] },
  { to: '/activity-calculator',label: 'Activity Guide',     icon: <Calculator size={18}/>,      roles: ['vendor'] },
  { to: '/vendors',            label: 'Vendors',            icon: <Building2 size={18}/>,       roles: ['admin','manager'] },
  { to: '/users',              label: 'User Management',    icon: <Users size={18}/>,           roles: ['admin'] },
  { to: '/emission-factors',   label: 'EF Library',         icon: <BarChart3 size={18}/>,       roles: ['admin'] },
  { to: '/reports',            label: 'Reports',            icon: <FileText size={18}/>,        roles: ['admin','manager','vendor','auditor'] },
  { to: '/audit',              label: 'Audit Log',          icon: <ClipboardCheck size={18}/>,  roles: ['admin','auditor'] },
  { to: '/settings',           label: 'Settings',           icon: <Settings size={18}/>,        roles: ['admin'] },
]

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }
  const visibleNav = NAV_ITEMS.filter(item => user && item.roles.includes(user.role))

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 bg-white border-r border-gray-100 flex flex-col">
        <div className="p-5 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center">
              <ShieldCheck size={16} className="text-white"/>
            </div>
            <div>
              <p className="text-sm font-bold text-gray-900 leading-none">ESG Platform</p>
              <p className="text-xs text-gray-400 mt-0.5">Scope 3 Module</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {visibleNav.map((item) => (
            <NavLink key={item.to} to={item.to}
              className={({ isActive }) => clsx('sidebar-link', isActive && 'active')}>
              {item.icon}{item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-100">
          <NavLink to="/profile"
            className={({ isActive }) => clsx('sidebar-link mb-1', isActive && 'active')}>
            <UserCircle size={18}/> My Profile
          </NavLink>
          <button onClick={handleLogout}
            className="sidebar-link w-full text-red-500 hover:bg-red-50 hover:text-red-600">
            <LogOut size={16}/> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-gray-100 px-6 py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 capitalize">{user?.role}</span>
            {user?.region && user.region !== 'all' && (
              <><span className="text-gray-200">·</span>
              <span className="text-xs text-gray-400 capitalize">{user.region} Region</span></>
            )}
          </div>
          <div className="flex items-center gap-2">
            <NotificationBell/>
            <NavLink to="/profile"
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl hover:bg-gray-50 transition-colors">
              <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center">
                <span className="text-xs font-semibold text-brand-700">
                  {user?.full_name?.[0] || user?.email?.[0] || '?'}
                </span>
              </div>
              <span className="text-sm font-medium text-gray-700 hidden sm:block">
                {user?.full_name || user?.email?.split('@')[0]}
              </span>
            </NavLink>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto p-6">{children}</div>
        </main>
      </div>
    </div>
  )
}
