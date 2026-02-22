'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  BarChart3,
  BookOpen,
  CalendarDays,
  LayoutDashboard,
  MessageSquare,
  ShieldCheck,
  Shuffle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Navigation items for the sidebar.
 * Each maps to one of the 7 core pages.
 */
const navItems = [
  { href: '/', label: '儀表板', icon: LayoutDashboard },
  { href: '/orders', label: '訂單管理', icon: BarChart3 },
  { href: '/schedule', label: '排程', icon: CalendarDays },
  { href: '/simulate', label: '模擬', icon: Shuffle },
  { href: '/chat', label: 'AI 對話', icon: MessageSquare },
  { href: '/knowledge', label: '知識庫', icon: BookOpen },
  { href: '/compliance', label: '合規', icon: ShieldCheck },
] as const

/**
 * Sidebar navigation component with links to all 7 core pages.
 * Highlights the active route. Collapses to icons on narrow viewports.
 */
export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex h-full w-56 flex-col border-r bg-background">
      {/* Logo / Brand */}
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-bold">
          AP
        </div>
        <span className="text-sm font-semibold tracking-tight">
          AutoPilot SME
        </span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === '/' ? pathname === '/' : pathname.startsWith(href)

          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">v0.1.0 MVP</p>
      </div>
    </aside>
  )
}
