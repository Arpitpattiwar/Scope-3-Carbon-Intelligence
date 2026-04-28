import { useEffect, useState, useRef } from 'react'
import { Bell, CheckCheck, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { notificationsApi } from '@/utils/api'
import clsx from 'clsx'

const TYPE_ICONS: Record<string, string> = {
  vendor_onboarded:  '🏭',
  record_submitted:  '📋',
  record_approved:   '✅',
  record_rejected:   '❌',
  vendor_invited:    '📧',
  report_ready:      '📊',
  period_locked:     '🔒',
  system:            '🔔',
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<any[]>([])
  const [unread, setUnread] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchUnread()
    const interval = setInterval(fetchUnread, 30000) // poll every 30s
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const fetchUnread = async () => {
    try {
      const res = await notificationsApi.unreadCount()
      setUnread(res.data.count)
    } catch {}
  }

  const fetchAll = async () => {
    try {
      const res = await notificationsApi.list()
      setNotifications(res.data)
    } catch {}
  }

  const handleOpen = () => {
    setOpen(v => !v)
    if (!open) fetchAll()
  }

  const markAllRead = async () => {
    await notificationsApi.markAllRead()
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
    setUnread(0)
  }

  const handleClick = async (n: any) => {
    if (!n.is_read) {
      await notificationsApi.markRead(n.id)
      setNotifications(prev => prev.map(x => x.id === n.id ? { ...x, is_read: true } : x))
      setUnread(prev => Math.max(0, prev - 1))
    }
    if (n.link) {
      setOpen(false)
      navigate(n.link)
    }
  }

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    const diff = Date.now() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
  }

  return (
    <div ref={ref} className="relative">
      <button onClick={handleOpen}
        className="relative p-2 rounded-xl hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700">
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 w-80 bg-white rounded-2xl shadow-2xl border border-gray-100 z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
            {unread > 0 && (
              <button onClick={markAllRead}
                className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium">
                <CheckCheck size={13}/> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-10 text-center text-sm text-gray-400">
                <Bell size={24} className="mx-auto mb-2 opacity-30"/>
                No notifications yet
              </div>
            ) : notifications.map((n: any) => (
              <button key={n.id} onClick={() => handleClick(n)}
                className={clsx(
                  'w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0',
                  !n.is_read && 'bg-brand-50/50'
                )}>
                <div className="flex items-start gap-3">
                  <span className="text-lg flex-shrink-0 mt-0.5">
                    {TYPE_ICONS[n.type] || '🔔'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className={clsx('text-xs font-semibold truncate',
                        n.is_read ? 'text-gray-600' : 'text-gray-900')}>
                        {n.title}
                      </p>
                      {!n.is_read && (
                        <span className="w-1.5 h-1.5 rounded-full bg-brand-500 flex-shrink-0"/>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.message}</p>
                    <p className="text-xs text-gray-400 mt-1">{formatTime(n.created_at)}</p>
                  </div>
                  {n.link && <ExternalLink size={12} className="text-gray-300 flex-shrink-0 mt-1"/>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
