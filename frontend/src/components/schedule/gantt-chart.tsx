'use client'

import { useMemo } from 'react'
import dynamic from 'next/dynamic'
import type { ScheduledJobResponse } from '@/lib/types'

// ─── Dynamic Import (ECharts does not support SSR) ──────────────────────────

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

// ─── Types ────────────────────────────────────────────────────────────────────

interface GanttChartProps {
  jobs: ScheduledJobResponse[]
}

// ─── Product Color Palette ──────────────────────────────────────────────────

const PRODUCT_COLORS = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
]

function getProductColor(productId: string, productIds: string[]): string {
  const index = productIds.indexOf(productId)
  return PRODUCT_COLORS[index % PRODUCT_COLORS.length]
}

// ─── Component ───────────────────────────────────────────────────────────────

export function GanttChart({ jobs }: GanttChartProps) {
  const option = useMemo(() => {
    if (jobs.length === 0) return null

    // Get unique production line IDs and product IDs
    const lineIds = [...new Set(jobs.map((j) => j.production_line_id))]
    const productIds = [...new Set(jobs.map((j) => j.product_id))]

    // Build short labels for Y-axis
    const lineLabels = lineIds.map((id) => `產線 ${id.slice(0, 6)}`)

    // Calculate time bounds
    const starts = jobs.map((j) => new Date(j.planned_start).getTime())
    const ends = jobs.map((j) => new Date(j.planned_end).getTime())
    const minTime = Math.min(...starts)
    const maxTime = Math.max(...ends)

    // Build data items for the custom series
    const data = jobs.map((job) => {
      const lineIndex = lineIds.indexOf(job.production_line_id)
      return {
        value: [
          lineIndex,
          new Date(job.planned_start).getTime(),
          new Date(job.planned_end).getTime(),
          job.product_id,
          job.quantity,
          job.status,
        ],
        itemStyle: {
          color: getProductColor(job.product_id, productIds),
        },
      }
    })

    // Legend data from unique products
    const legendData = productIds.map((pid) => ({
      name: `產品 ${pid.slice(0, 6)}`,
      itemStyle: { color: getProductColor(pid, productIds) },
    }))

    return {
      tooltip: {
        formatter(params: { value: [number, number, number, string, number, string] }) {
          const [, start, end, productId, quantity, status] = params.value
          const startStr = new Date(start).toLocaleString('zh-TW')
          const endStr = new Date(end).toLocaleString('zh-TW')
          const durationMin = Math.round((end - start) / 60000)
          return [
            `<strong>產品:</strong> ${productId.slice(0, 8)}`,
            `<strong>數量:</strong> ${quantity.toLocaleString()}`,
            `<strong>狀態:</strong> ${status}`,
            `<strong>開始:</strong> ${startStr}`,
            `<strong>結束:</strong> ${endStr}`,
            `<strong>時長:</strong> ${durationMin} 分鐘`,
          ].join('<br/>')
        },
      },
      legend: {
        data: legendData.map((d) => d.name),
        bottom: 0,
      },
      grid: {
        left: 120,
        right: 40,
        top: 20,
        bottom: 60,
      },
      xAxis: {
        type: 'time' as const,
        min: minTime,
        max: maxTime,
        axisLabel: {
          formatter: '{MM}/{dd} {HH}:{mm}',
        },
      },
      yAxis: {
        type: 'category' as const,
        data: lineLabels,
        inverse: true,
      },
      series: [
        {
          type: 'custom' as const,
          renderItem(
            params: { coordSys: { x: number; y: number; width: number; height: number } },
            api: {
              value: (idx: number) => number
              coord: (val: [number, number]) => [number, number]
              size: (val: [number, number]) => [number, number]
              style: () => Record<string, unknown>
            },
          ) {
            const lineIndex = api.value(0)
            const start = api.coord([api.value(1), lineIndex])
            const end = api.coord([api.value(2), lineIndex])
            const barHeight = api.size([0, 1])[1] * 0.6

            return {
              type: 'rect',
              shape: {
                x: start[0],
                y: start[1] - barHeight / 2,
                width: Math.max(end[0] - start[0], 2),
                height: barHeight,
                r: 3,
              },
              style: api.style(),
            }
          },
          encode: {
            x: [1, 2],
            y: 0,
          },
          data,
        },
      ],
      dataZoom: [
        {
          type: 'slider' as const,
          xAxisIndex: 0,
          filterMode: 'none' as const,
          bottom: 30,
          height: 20,
        },
      ],
    }
  }, [jobs])

  if (jobs.length === 0 || !option) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border text-muted-foreground">
        尚無排程資料，請先執行排程
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <ReactECharts
        option={option}
        style={{ height: Math.max(300, option.yAxis.data.length * 60) }}
        notMerge
      />
    </div>
  )
}
