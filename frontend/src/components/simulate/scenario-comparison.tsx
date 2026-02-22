'use client'

import { AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RushOrderScenario } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScenarioComparisonProps {
  scenarios: RushOrderScenario[]
  recommendedScenario: string | null
}

// ─── Single Scenario Card ────────────────────────────────────────────────────

function ScenarioCard({ scenario, isRecommended }: { scenario: RushOrderScenario; isRecommended: boolean }) {
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
        <h3 className="text-lg font-semibold">{scenario.name}</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {scenario.description}
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">產線</p>
          <p className="text-sm font-semibold">{scenario.production_line_name}</p>
        </div>
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">完成時間</p>
          <p className="text-sm font-semibold">
            {new Date(scenario.completion_time).toLocaleString('zh-TW')}
          </p>
        </div>
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">生產時數</p>
          <p className="text-sm font-semibold">{scenario.production_hours} hr</p>
        </div>
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">換線時間</p>
          <p className="text-sm font-semibold">{scenario.changeover_time} min</p>
        </div>
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">加班時數</p>
          <p className="text-sm font-semibold">{scenario.overtime_hours.toFixed(1)} hr</p>
        </div>
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">額外成本</p>
          <p className="text-sm font-semibold">NT$ {scenario.additional_cost.toLocaleString()}</p>
        </div>
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">如期交貨</p>
          <p className={cn('text-sm font-semibold', scenario.meets_target ? 'text-emerald-600' : 'text-destructive')}>
            {scenario.meets_target ? '是' : '否'}
          </p>
        </div>
        <div className="rounded-md border bg-muted/30 px-3 py-2">
          <p className="text-xs text-muted-foreground">受影響訂單</p>
          <p className="text-sm font-semibold">{scenario.affected_orders.length}</p>
        </div>
      </div>

      {/* Affected Orders */}
      {scenario.affected_orders.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1.5 text-sm font-medium text-amber-600">
            <AlertTriangle className="h-3.5 w-3.5" />
            受影響訂單 ({scenario.affected_orders.length})
          </div>
          <div className="mt-1.5 space-y-1">
            {scenario.affected_orders.map((ao) => (
              <div
                key={ao.order_item_id}
                className="rounded-md border bg-amber-50 px-3 py-1.5 text-xs text-amber-700"
              >
                延遲 {ao.delay_minutes.toFixed(0)} 分鐘
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {scenario.warnings.length > 0 && (
        <div className="space-y-1.5">
          {scenario.warnings.map((warning, i) => (
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
export function ScenarioComparison({ scenarios, recommendedScenario }: ScenarioComparisonProps) {
  if (scenarios.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">模擬結果比較</h2>
        <p className="text-sm text-muted-foreground">
          共 {scenarios.length} 個方案
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {scenarios.map((scenario) => (
          <ScenarioCard
            key={scenario.name}
            scenario={scenario}
            isRecommended={scenario.name === recommendedScenario}
          />
        ))}
      </div>
    </div>
  )
}
