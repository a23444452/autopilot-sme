'use client'

import { useState } from 'react'
import { CalendarDays, Filter, RefreshCw, BarChart3, Table2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ProductionLineResponse } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

export type ViewMode = 'gantt' | 'table'

export type ScheduleStrategy = 'balanced' | 'rush' | 'efficiency'

export interface ScheduleFilters {
  startDate: string
  endDate: string
  lineId: string
  strategy: ScheduleStrategy
}

interface ScheduleToolbarProps {
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
  filters: ScheduleFilters
  onFiltersChange: (filters: ScheduleFilters) => void
  lines: ProductionLineResponse[]
  onRegenerate: () => void
  isRegenerating: boolean
}

// ─── Strategy Labels ────────────────────────────────────────────────────────

const STRATEGY_LABELS: Record<ScheduleStrategy, string> = {
  balanced: '平衡',
  rush: '趕工',
  efficiency: '效率優先',
}

// ─── Component ───────────────────────────────────────────────────────────────

export function ScheduleToolbar({
  viewMode,
  onViewModeChange,
  filters,
  onFiltersChange,
  lines,
  onRegenerate,
  isRegenerating,
}: ScheduleToolbarProps) {
  function updateFilter<K extends keyof ScheduleFilters>(key: K, value: ScheduleFilters[K]) {
    onFiltersChange({ ...filters, [key]: value })
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* View Toggle */}
      <div className="flex rounded-md border">
        <button
          onClick={() => onViewModeChange('gantt')}
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium',
            viewMode === 'gantt'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-muted',
          )}
        >
          <BarChart3 className="h-4 w-4" />
          甘特圖
        </button>
        <button
          onClick={() => onViewModeChange('table')}
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium',
            viewMode === 'table'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-muted',
          )}
        >
          <Table2 className="h-4 w-4" />
          表格
        </button>
      </div>

      {/* Date Filters */}
      <div className="flex items-center gap-2">
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
        <input
          type="date"
          value={filters.startDate}
          onChange={(e) => updateFilter('startDate', e.target.value)}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        />
        <span className="text-sm text-muted-foreground">至</span>
        <input
          type="date"
          value={filters.endDate}
          onChange={(e) => updateFilter('endDate', e.target.value)}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        />
      </div>

      {/* Line Filter */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <select
          value={filters.lineId}
          onChange={(e) => updateFilter('lineId', e.target.value)}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        >
          <option value="">全部產線</option>
          {lines.map((line) => (
            <option key={line.id} value={line.id}>
              {line.name}
            </option>
          ))}
        </select>
      </div>

      {/* Strategy */}
      <select
        value={filters.strategy}
        onChange={(e) => updateFilter('strategy', e.target.value as ScheduleStrategy)}
        className="rounded-md border bg-background px-3 py-1.5 text-sm"
      >
        {(Object.entries(STRATEGY_LABELS) as [ScheduleStrategy, string][]).map(
          ([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ),
        )}
      </select>

      {/* Regenerate */}
      <button
        onClick={onRegenerate}
        disabled={isRegenerating}
        className="ml-auto inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        <RefreshCw className={cn('h-4 w-4', isRegenerating && 'animate-spin')} />
        {isRegenerating ? '排程中...' : '重新排程'}
      </button>
    </div>
  )
}
