'use client'

import { cn } from '@/lib/utils'
import type { ProductionLineResponse } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface LineWithProgress extends ProductionLineResponse {
  /** Current progress as fraction (0-1). Derived from scheduled jobs. */
  progress: number
  /** Number of active jobs on this line. */
  activeJobs: number
}

interface LineStatusProps {
  lines: LineWithProgress[]
}

// ─── Status badge color ───────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status) {
    case 'active':
      return 'bg-emerald-500'
    case 'maintenance':
      return 'bg-amber-500'
    case 'idle':
      return 'bg-muted-foreground'
    default:
      return 'bg-muted-foreground'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'active':
      return '運行中'
    case 'maintenance':
      return '維護中'
    case 'idle':
      return '閒置'
    default:
      return status
  }
}

// ─── Line Status Component ────────────────────────────────────────────────────

/**
 * Shows each production line with a progress bar, status indicator, and
 * active job count.
 */
export function LineStatus({ lines }: LineStatusProps) {
  if (lines.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-sm font-medium text-muted-foreground">產線狀態</h3>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          尚無產線資料
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-muted-foreground">產線狀態</h3>
      <div className="space-y-4">
        {lines.map((line) => (
          <div key={line.id} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span
                  className={cn('inline-block h-2 w-2 rounded-full', statusColor(line.status))}
                  aria-label={statusLabel(line.status)}
                />
                <span className="font-medium">{line.name}</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>{line.activeJobs} 個工單</span>
                <span>{(line.progress * 100).toFixed(0)}%</span>
              </div>
            </div>
            {/* Progress bar */}
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  line.status === 'active' ? 'bg-primary' : 'bg-muted-foreground/40',
                )}
                style={{ width: `${Math.min(line.progress * 100, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
