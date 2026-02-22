'use client'

import { Search, Zap, BarChart3, FileText } from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────────────────────

interface QuickAction {
  label: string
  message: string
  icon: React.ReactNode
}

interface QuickActionsProps {
  onSelect: (message: string) => void
  disabled?: boolean
}

// ─── Quick Actions ───────────────────────────────────────────────────────────

const actions: QuickAction[] = [
  {
    label: '查交期',
    message: '請幫我查詢目前所有訂單的交期狀態，哪些即將到期或已逾期？',
    icon: <Search className="h-4 w-4" />,
  },
  {
    label: '模擬急單',
    message: '我想模擬一張急單插入現有排程，請協助分析影響。',
    icon: <Zap className="h-4 w-4" />,
  },
  {
    label: '查產能',
    message: '請查詢目前各產線的產能利用率與狀態。',
    icon: <BarChart3 className="h-4 w-4" />,
  },
  {
    label: '本週報表',
    message: '請生成本週的生產排程報表摘要，包含關鍵指標。',
    icon: <FileText className="h-4 w-4" />,
  },
]

/**
 * Quick action buttons for common chat queries.
 * Displayed when the conversation is empty to help users get started.
 */
export function QuickActions({ onSelect, disabled }: QuickActionsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {actions.map((action) => (
        <button
          key={action.label}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(action.message)}
          className="flex flex-col items-center gap-2 rounded-lg border bg-card p-4 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
            {action.icon}
          </span>
          {action.label}
        </button>
      ))}
    </div>
  )
}
