'use client'

import {
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Clock,
  Gauge,
  Minus,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface KpiData {
  onTimeRate: number
  onTimeTrend: number
  utilization: number
  utilizationTrend: number
  qualityRate: number
  qualityTrend: number
  overtimeHours: number
  overtimeTrend: number
}

interface KpiCardProps {
  title: string
  value: string
  trend: number
  icon: React.ReactNode
  /** Higher is better? Used to color the trend indicator. */
  higherIsBetter?: boolean
}

// ─── Single KPI Card ──────────────────────────────────────────────────────────

function KpiCard({ title, value, trend, icon, higherIsBetter = true }: KpiCardProps) {
  const trendDirection = trend > 0 ? 'up' : trend < 0 ? 'down' : 'flat'
  const isPositive =
    trendDirection === 'flat'
      ? null
      : higherIsBetter
        ? trendDirection === 'up'
        : trendDirection === 'down'

  const TrendIcon =
    trendDirection === 'up' ? ArrowUp : trendDirection === 'down' ? ArrowDown : Minus

  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <div className="text-muted-foreground">{icon}</div>
      </div>
      <div className="mt-2 flex items-end justify-between">
        <p className="text-2xl font-bold tracking-tight">{value}</p>
        <div
          className={cn(
            'flex items-center gap-0.5 text-xs font-medium',
            isPositive === null && 'text-muted-foreground',
            isPositive === true && 'text-emerald-600',
            isPositive === false && 'text-destructive',
          )}
        >
          <TrendIcon className="h-3 w-3" />
          {Math.abs(trend).toFixed(1)}%
        </div>
      </div>
    </div>
  )
}

// ─── KPI Cards Grid ───────────────────────────────────────────────────────────

interface KpiCardsProps {
  data: KpiData
}

/**
 * Four KPI cards showing on-time rate, utilization, quality, and overtime
 * with trend indicators comparing to previous period.
 */
export function KpiCards({ data }: KpiCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        title="準時交貨率"
        value={`${(data.onTimeRate * 100).toFixed(1)}%`}
        trend={data.onTimeTrend}
        icon={<CheckCircle2 className="h-4 w-4" />}
        higherIsBetter
      />
      <KpiCard
        title="產線稼動率"
        value={`${(data.utilization * 100).toFixed(1)}%`}
        trend={data.utilizationTrend}
        icon={<Gauge className="h-4 w-4" />}
        higherIsBetter
      />
      <KpiCard
        title="品質達成率"
        value={`${(data.qualityRate * 100).toFixed(1)}%`}
        trend={data.qualityTrend}
        icon={<Zap className="h-4 w-4" />}
        higherIsBetter
      />
      <KpiCard
        title="加班時數"
        value={`${data.overtimeHours.toFixed(0)} hr`}
        trend={data.overtimeTrend}
        icon={<Clock className="h-4 w-4" />}
        higherIsBetter={false}
      />
    </div>
  )
}
