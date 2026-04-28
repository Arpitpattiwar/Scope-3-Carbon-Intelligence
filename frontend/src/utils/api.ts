import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

export const authApi = {
  login: (email: string, password: string) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
}

export const profileApi = {
  get: () => api.get('/profile'),
  update: (data: any) => api.patch('/profile', data),
  changePassword: (data: any) => api.post('/profile/change-password', data),
  changeEmail: (data: any) => api.post('/profile/change-email', data),
  getVendorDetails: () => api.get('/profile/vendor-details'),
  updateVendorDetails: (data: any) => api.patch('/profile/vendor-details', data),
}

export const usersApi = {
  list: (role?: string) => api.get('/users', { params: { role } }),
  create: (data: any) => api.post('/users', data),
  get: (id: number) => api.get(`/users/${id}`),
  update: (id: number, data: any) => api.patch(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
  inviteVendor: (data: any) => api.post('/users/invite-vendor', data),
  listInvitations: () => api.get('/users/invitations/list'),
  listVendors: (region?: string) => api.get('/users/vendors', { params: { region } }),
  getVendor: (id: number) => api.get(`/users/vendors/${id}`),
  onboard: (data: any) => api.post('/users/onboard', data),
}

export const emissionsApi = {
  list: (params?: any) => api.get('/emissions', { params }),
  create: (data: any) => api.post('/emissions', data),
  uploadCsv: (file: File) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post('/emissions/upload-csv', fd)
  },
  getTrace: (id: number) => api.get(`/emissions/${id}/trace`),
  updateStatus: (id: number, status: string, notes?: string) =>
    api.patch(`/emissions/${id}/status`, { status, notes }),
}

export const dashboardApi = {
  summary: (params?: any) => api.get('/dashboard/summary', { params }),
  categoryBreakdown: (params?: any) => api.get('/dashboard/category-breakdown', { params }),
  regionBreakdown: (params?: any) => api.get('/dashboard/region-breakdown', { params }),
  trend: (params?: any) => api.get('/dashboard/trend', { params }),
  topVendors: (params?: any) => api.get('/dashboard/top-vendors', { params }),
  vendorEngagement: () => api.get('/dashboard/vendor-engagement'),
}

export const efApi = {
  list: (params?: any) => api.get('/emission-factors', { params }),
  create: (data: any) => api.post('/emission-factors', data),
  deactivate: (id: number) => api.delete(`/emission-factors/${id}`),
}

export const auditApi = {
  logs: (params?: any) => api.get('/audit/logs', { params }),
  exportCsv: () => api.get('/audit/logs/export-csv', { responseType: 'blob' }),
}

export const notificationsApi = {
  list: () => api.get('/notifications'),
  unreadCount: () => api.get('/notifications/unread-count'),
  markRead: (id: number) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
}

export const reportsApi = {
  downloadExcel: (params?: any) => api.get('/reports/download-excel', {
    params, responseType: 'blob',
  }),
  csvTemplate: () => api.get('/reports/csv-template', { responseType: 'blob' }),
}

export const periodsApi = {
  list: () => api.get('/reporting-periods'),
  create: (data: any) => api.post('/reporting-periods', data),
  lock: (id: number) => api.post(`/reporting-periods/${id}/lock`),
}

export const targetsApi = {
  list: (year?: number) => api.get('/targets', { params: year ? { year } : {} }),
  create: (data: any) => api.post('/targets', data),
  delete: (id: number) => api.delete(`/targets/${id}`),
}

export const vendorApi = {
  history: (year?: number) => api.get('/vendor/history', { params: year ? { year } : {} }),
  intensity: () => api.get('/vendor/intensity'),
  exportCsv: (year?: number) => api.get('/vendor/export-csv', { params: year ? { year } : {}, responseType: 'blob' }),
  brsrExport: (year?: number) => api.get('/vendor/brsr-export', { params: year ? { year } : {}, responseType: 'blob' }),
  bulkReminder: () => api.post('/vendor/bulk-reminder'),
}

export const attachmentsApi = {
  list: (recordId: number) => api.get(`/attachments/${recordId}`),
  upload: (recordId: number, file: File, description?: string) => {
    const fd = new FormData()
    fd.append('file', file)
    if (description) fd.append('description', description)
    return api.post(`/attachments/${recordId}`, fd)
  },
  delete: (attachmentId: number) => api.delete(`/attachments/${attachmentId}`),
}
