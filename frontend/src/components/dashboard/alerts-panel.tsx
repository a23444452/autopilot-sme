'use client'

import { AlertTriangle, Clock, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

export type AlertSeverity = 'warning' | 'danger' | 'info'

export interface AlertItem {
  id: string
  severity: AlertSeverity
  title: string
  description: string
  timestamp: string
}

interface AlertsPanelProps {
  alerts: AlertItem[]
}

// ─── Severity styling ─────────────────────────────────────────────────────────

function severityConfig(severity: AlertSeverity) {
  switch (severity) {
    case 'danger':
      return {
        icon: AlertTriangle,
        bg: 'bg-destructive/10',
        text: 'text-destructive',
        border: 'border-destructive/20',
      }
    case 'warning':
      return {
        icon: Clock,
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        border: 'border-amber-200',
      }
    case 'info':
    default:
      return {
        icon: Info,
        bg: 'bg-blue-50',
        text: 'text-blue-700',
        border: 'border-blue-200',
      }
  }
}

// ─── Alerts Panel Component ───────────────────────────────────────────────────

/**
 * Panel showing pending warnings and at-risk orders.
 * Sorted by severity (danger first) then timestamp.
 */
export function AlertsPanel({ alerts }: AlertsPanelProps) {
  if (alerts.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-sm font-medium text-muted-foreground">警示通知</h3>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          目前無警示
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-muted-foreground">警示通知</h3>
        <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">
          {alerts.length}
        </span>
      </div>
      <div className="space-y-3">
        {alerts.map((alert) => {
          const config = severityConfig(alert.severity)
          const Icon = config.icon

          return (
            <div
              key={alert.id}
              className={cn(
                'flex gap-3 rounded-md border p-3',
                config.bg,
                config.border,
              )}
            >
              <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', config.text)} />
              <div className="min-w-0 flex-1">
                <p className={cn('text-sm font-medium', config.text)}>
                  {alert.title}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {alert.description}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
