'use client'

import { useMemo } from 'react'
import dynamic from 'next/dynamic'
import type { UsageStats } from '@/lib/types'

// ─── Dynamic Import (ECharts does not support SSR) ──────────────────────────

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

// ─── Types ────────────────────────────────────────────────────────────────────

interface UsageChartProps {
  stats: UsageStats
}

// ─── Provider Color Palette ─────────────────────────────────────────────────

const PROVIDER_COLORS: Record<string, string> = {
  anthropic: '#d97706',
  openai: '#10b981',
  ollama: '#3b82f6',
}

const DEFAULT_COLORS = ['#8b5cf6', '#ec4899', '#06b6d4', '#f97316', '#84cc16']

function getProviderColor(provider: string, idx: number): string {
  return PROVIDER_COLORS[provider.toLowerCase()] ?? DEFAULT_COLORS[idx % DEFAULT_COLORS.length]
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Usage chart showing AI model usage breakdown by provider.
 * Uses ECharts pie + bar charts with dynamic import (no SSR).
 */
export function UsageChart({ stats }: UsageChartProps) {
  const pieOption = useMemo(() => {
    const providers = Object.entries(stats.calls_by_provider)
    if (providers.length === 0) return null

    return {
      tooltip: {
        trigger: 'item' as const,
        formatter: '{b}: {c} 次 ({d}%)',
      },
      legend: {
        bottom: 0,
        data: providers.map(([name]) => name),
      },
      series: [
        {
          type: 'pie' as const,
          radius: ['40%', '70%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: { show: false },
          emphasis: {
            label: { show: true, fontSize: 14, fontWeight: 'bold' },
          },
          data: providers.map(([name, value], idx) => ({
            name,
            value,
            itemStyle: { color: getProviderColor(name, idx) },
          })),
        },
      ],
    }
  }, [stats.calls_by_provider])

  const barOption = useMemo(() => {
    const taskTypes = Object.entries(stats.calls_by_task_type)
    if (taskTypes.length === 0) return null

    return {
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
      },
      grid: {
        left: 80,
        right: 20,
        top: 10,
        bottom: 30,
      },
      xAxis: {
        type: 'value' as const,
        name: '呼叫次數',
      },
      yAxis: {
        type: 'category' as const,
        data: taskTypes.map(([name]) => name),
        inverse: true,
      },
      series: [
        {
          type: 'bar' as const,
          data: taskTypes.map(([, value]) => value),
          itemStyle: {
            color: '#3b82f6',
            borderRadius: [0, 4, 4, 0],
          },
          barMaxWidth: 30,
        },
      ],
    }
  }, [stats.calls_by_task_type])

  if (!pieOption && !barOption) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border text-muted-foreground">
        尚無使用統計資料
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Provider Breakdown */}
      {pieOption && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">依供應商分佈</h3>
          <ReactECharts option={pieOption} style={{ height: 280 }} notMerge />
        </div>
      )}

      {/* Task Type Breakdown */}
      {barOption && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">依任務類型分佈</h3>
          <ReactECharts option={barOption} style={{ height: 280 }} notMerge />
        </div>
      )}
    </div>
  )
}
