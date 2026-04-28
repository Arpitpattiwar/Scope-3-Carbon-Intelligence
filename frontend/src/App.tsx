import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/utils/api'
import AppLayout from '@/components/layout/AppLayout'

import LoginPage from '@/pages/auth/LoginPage'
import ChangePasswordPage from '@/pages/auth/ChangePasswordPage'
import DashboardPage from '@/pages/DashboardPage'
import EmissionsPage from '@/pages/EmissionsPage'
import ReportsPage from '@/pages/ReportsPage'
import AuditPage from '@/pages/AuditPage'
import OnboardingPage from '@/pages/vendor/OnboardingPage'
import SubmitDataPage from '@/pages/vendor/SubmitDataPage'
import SubmissionHistory from '@/pages/vendor/SubmissionHistory'
import ActivityCalculator from '@/pages/vendor/ActivityCalculator'
import VendorsPage from '@/pages/manager/VendorsPage'
import UsersPage from '@/pages/admin/UsersPage'
import EFLibraryPage from '@/pages/admin/EFLibraryPage'
import SettingsPage from '@/pages/admin/SettingsPage'
import ProfilePage from '@/pages/profile/ProfilePage'

function RequireAuth({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (roles && user && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function RequireOnboarding({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore()
  if (user?.must_change_password) return <Navigate to="/change-password" replace />
  if (user?.role === 'vendor' && !user.onboarding_complete) return <Navigate to="/onboarding" replace />
  return <>{children}</>
}

function Wrap({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  return (
    <RequireAuth roles={roles}>
      <RequireOnboarding>
        <AppLayout>{children}</AppLayout>
      </RequireOnboarding>
    </RequireAuth>
  )
}

export default function App() {
  const { isAuthenticated, updateUser, logout } = useAuthStore()

  useEffect(() => {
    if (!isAuthenticated) return
    authApi.me().then(res => updateUser(res.data)).catch(() => logout())
  }, [])

  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{
        className: '!rounded-xl !text-sm !font-medium !shadow-lg !bg-white !text-gray-900',
        duration: 3500,
      }}/>
      <Routes>
        <Route path="/login"           element={isAuthenticated ? <Navigate to="/dashboard" replace/> : <LoginPage/>}/>
        <Route path="/change-password" element={<RequireAuth><ChangePasswordPage/></RequireAuth>}/>
        <Route path="/onboarding"      element={<RequireAuth roles={['vendor']}><OnboardingPage/></RequireAuth>}/>

        <Route path="/dashboard"          element={<Wrap><DashboardPage/></Wrap>}/>
        <Route path="/emissions"          element={<Wrap><EmissionsPage/></Wrap>}/>
        <Route path="/submit"             element={<Wrap roles={['vendor']}><SubmitDataPage/></Wrap>}/>
        <Route path="/history"            element={<Wrap roles={['vendor']}><SubmissionHistory/></Wrap>}/>
        <Route path="/activity-calculator" element={<Wrap roles={['vendor']}><ActivityCalculator/></Wrap>}/>
        <Route path="/vendors"            element={<Wrap roles={['admin','manager']}><VendorsPage/></Wrap>}/>
        <Route path="/users"              element={<Wrap roles={['admin']}><UsersPage/></Wrap>}/>
        <Route path="/emission-factors"   element={<Wrap roles={['admin']}><EFLibraryPage/></Wrap>}/>
        <Route path="/reports"            element={<Wrap><ReportsPage/></Wrap>}/>
        <Route path="/audit"              element={<Wrap roles={['admin','auditor']}><AuditPage/></Wrap>}/>
        <Route path="/settings"           element={<Wrap roles={['admin']}><SettingsPage/></Wrap>}/>
        <Route path="/profile"            element={<Wrap><ProfilePage/></Wrap>}/>

        <Route path="/" element={<Navigate to="/dashboard" replace/>}/>
        <Route path="*" element={<Navigate to="/dashboard" replace/>}/>
      </Routes>
    </BrowserRouter>
  )
}
