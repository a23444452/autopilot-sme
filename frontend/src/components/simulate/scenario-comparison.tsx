'use client'

import { CheckCircle2, AlertTriangle, Clock, DollarSign } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SimulationResult } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScenarioComparisonProps {
  results: SimulationResult[]
}

// ─── Helper ──────────────────────────────────────────────────────────────────

function formatMetricLabel(key: string): string {
  const labels: Record<string, string> = {
    on_time_rate: '準時交貨率',
    utilization: '產線稼動率',
    overtime_hours: '加班時數',
    changeover_time: '換線時間',
    completion_days: '完成天數',
    delay_days: '延遲天數',
    additional_cost: '額外成本',
    affected_orders: '受影響訂單',
  }
  return labels[key] ?? key
}

function formatMetricValue(key: string, value: number): string {
  if (key.includes('rate') || key.includes('utilization')) {
    return `${(value * 100).toFixed(1)}%`
  }
  if (key.includes('cost')) {
    return `NT$ ${value.toLocaleString()}`
  }
  if (key.includes('hours') || key.includes('time')) {
    return `${value.toFixed(1)} hr`
  }
  if (key.includes('days')) {
    return `${value.toFixed(0)} 天`
  }
  return String(value)
}

// ─── Single Scenario Card ────────────────────────────────────────────────────

function ScenarioCard({ result, isRecommended }: { result: SimulationResult; isRecommended: boolean }) {
  const metricEntries = Object.entries(result.metrics)
  const affectedOrders = result.comparison?.affected_orders as string[] | undefined

  return (
    <div
      className={cn(
        'relative rounded-lg border bg-card p-5 shadow-sm',
        isRecommended && 'border-emerald-500 ring-1 ring-emerald-500/20',
      )}
    >
      {/* Recommendation Badge */}
      {isRecommended && (
        <div className="absolute -top-2.5 left-4 rounded-full bg-emerald-500 px-3 py-0.5 text-xs font-medium text-white">
          推薦方案
        </div>
      )}

      {/* Scenario Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold">{result.scenario_name}</h3>
        {result.metadata?.description != null && (
          <p className="mt-1 text-sm text-muted-foreground">
            {String(result.metadata.description)}
          </p>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        {metricEntries.map(([key, value]) => (
          <div key={key} className="rounded-md border bg-muted/30 px-3 py-2">
            <p className="text-xs text-muted-foreground">{formatMetricLabel(key)}</p>
            <p className="text-sm font-semibold">{formatMetricValue(key, value)}</p>
          </div>
        ))}
      </div>

      {/* Affected Orders */}
      {affectedOrders && affectedOrders.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1.5 text-sm font-medium text-amber-600">
            <AlertTriangle className="h-3.5 w-3.5" />
            受影響訂單 ({affectedOrders.length})
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {affectedOrders.map((orderId) => (
              <span
                key={orderId}
                className="rounded-full border bg-amber-50 px-2 py-0.5 text-xs text-amber-700"
              >
                {orderId}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="space-y-1.5">
          {result.warnings.map((warning, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
              {warning}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Scenario Comparison ─────────────────────────────────────────────────────

/**
 * Side-by-side scenario comparison cards showing impact details,
 * affected orders, costs, and recommendation badge for the best option.
 */
export function ScenarioComparison({ results }: ScenarioComparisonProps) {
  if (results.length === 0) {
    return null
  }

  // The first result with metadata.recommended === true, or the first one
  const recommendedIndex = results.findIndex(
    (r) => r.metadata?.recommended === true,
  )
  const bestIndex = recommendedIndex >= 0 ? recommendedIndex : 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">模擬結果比較</h2>
        <p className="text-sm text-muted-foreground">
          共 {results.length} 個方案
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {results.map((result, index) => (
          <ScenarioCard
            key={result.scenario_name}
            result={result}
            isRecommended={index === bestIndex}
          />
        ))}
      </div>
    </div>
  )
}
