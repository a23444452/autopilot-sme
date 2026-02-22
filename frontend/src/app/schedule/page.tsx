'use client'

import { useState, useMemo } from 'react'
import { AlertTriangle } from 'lucide-react'
import { useApi, useMutation } from '@/hooks/use-api'
import { getCurrentSchedule, generateSchedule, listProductionLines } from '@/lib/api'
import type { ScheduledJobResponse, ScheduleRequest, ScheduleResult, ProductionLineResponse } from '@/lib/types'
import { formatPercent, formatDuration, formatNumber } from '@/lib/utils'
import { ScheduleToolbar, type ViewMode, type ScheduleFilters } from '@/components/schedule/schedule-toolbar'
import { GanttChart } from '@/components/schedule/gantt-chart'
import { ScheduleTable } from '@/components/schedule/schedule-table'

// ─── Default Filters ────────────────────────────────────────────────────────

function getDefaultFilters(): ScheduleFilters {
  const today = new Date()
  const nextWeek = new Date(today)
  nextWeek.setDate(today.getDate() + 14)
  return {
    startDate: today.toISOString().slice(0, 10),
    endDate: nextWeek.toISOString().slice(0, 10),
    lineId: '',
    strategy: 'balanced',
  }
}

// ─── Page Component ─────────────────────────────────────────────────────────

/**
 * Schedule center page — view and regenerate production schedules.
 * Supports Gantt chart and table view modes.
 */
export default function SchedulePage() {
  const [viewMode, setViewMode] = useState<ViewMode>('gantt')
  const [filters, setFilters] = useState<ScheduleFilters>(getDefaultFilters)

  // Fetch current schedule (returns job list, not ScheduleResult)
  const {
    data: jobs,
    isLoading,
    error,
    refetch,
  } = useApi<ScheduledJobResponse[]>(
    () =>
      getCurrentSchedule(
        filters.lineId ? { production_line_id: filters.lineId } : undefined,
      ),
    { deps: [filters.lineId] },
  )

  // Regenerate returns ScheduleResult with metrics
  const [scheduleMetrics, setScheduleMetrics] = useState<ScheduleResult | null>(null)

  // Fetch production lines for the filter dropdown
  const { data: lines } = useApi<ProductionLineResponse[]>(
    () => listProductionLines({ limit: 100 }),
  )

  // Regenerate mutation
  const { mutate: doRegenerate, isLoading: isRegenerating } = useMutation<
    ScheduleResult,
    ScheduleRequest
  >((data) => generateSchedule(data))

  async function handleRegenerate() {
    const result = await doRegenerate({
      strategy: filters.strategy,
      horizon_days: 14,
    })
    if (result) {
      setScheduleMetrics(result)
      await refetch()
    }
  }

  // Filter jobs by date range
  const filteredJobs = useMemo(() => {
    if (!jobs) return []
    return jobs.filter((job) => {
      const start = new Date(job.planned_start)
      if (filters.startDate && start < new Date(filters.startDate)) return false
      if (filters.endDate && start > new Date(filters.endDate + 'T23:59:59')) return false
      return true
    })
  }, [jobs, filters.startDate, filters.endDate])

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">排程中心</h1>
        <p className="text-sm text-muted-foreground">
          檢視與管理生產排程，支援甘特圖和表格檢視
        </p>
      </div>

      {/* Toolbar */}
      <ScheduleToolbar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        filters={filters}
        onFiltersChange={setFilters}
        lines={lines ?? []}
        onRegenerate={handleRegenerate}
        isRegenerating={isRegenerating}
      />

      {/* KPI Summary */}
      {jobs && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">排程工作數</p>
            <p className="text-2xl font-bold">{formatNumber(scheduleMetrics?.total_jobs ?? jobs.length)}</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">產線利用率</p>
            <p className="text-2xl font-bold">{formatPercent((scheduleMetrics?.utilization_pct ?? 0) / 100)}</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">換線總時間</p>
            <p className="text-2xl font-bold">{formatDuration(scheduleMetrics?.total_changeover_minutes ?? 0)}</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">目前篩選</p>
            <p className="text-2xl font-bold">{filteredJobs.length}</p>
          </div>
        </div>
      )}

      {/* Warnings */}
      {scheduleMetrics?.warnings && scheduleMetrics.warnings.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
            <AlertTriangle className="h-4 w-4" />
            排程警告
          </div>
          <ul className="mt-1 list-inside list-disc text-sm text-amber-700">
            {scheduleMetrics.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Loading / Error */}
      {isLoading && (
        <div className="py-12 text-center text-muted-foreground">載入排程中...</div>
      )}
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          載入排程失敗: {error.message}
        </div>
      )}

      {/* Schedule View */}
      {jobs && (
        viewMode === 'gantt' ? (
          <GanttChart jobs={filteredJobs} />
        ) : (
          <ScheduleTable jobs={filteredJobs} />
        )
      )}
    </div>
  )
}
