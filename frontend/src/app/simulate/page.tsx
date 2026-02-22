'use client'

import { useState } from 'react'
import { Zap } from 'lucide-react'
import { useMutation } from '@/hooks/use-api'
import { simulateRushOrder } from '@/lib/api'
import type { SimulationRequest, SimulationResult } from '@/lib/types'
import { SimulationForm, type SimulationFormData } from '@/components/simulate/simulation-form'
import { ScenarioComparison } from '@/components/simulate/scenario-comparison'

// ─── Page Component ──────────────────────────────────────────────────────────

/**
 * Rush order simulation page – accepts product/quantity/date input
 * and displays multi-scenario what-if analysis results.
 */
export default function SimulatePage() {
  const [results, setResults] = useState<SimulationResult[] | null>(null)

  const { mutate: doSimulate, isLoading } = useMutation<SimulationResult[], SimulationRequest>(
    (data) => simulateRushOrder(data),
  )

  async function handleSimulate(formData: SimulationFormData) {
    const request: SimulationRequest = {
      scenarios: [
        {
          name: '標準插單',
          description: '依優先順序插入現有排程',
          changes: {
            product_id: formData.product_id,
            quantity: formData.quantity,
            target_date: formData.target_date,
            strategy: 'balanced',
          },
        },
        {
          name: '加急處理',
          description: '最高優先，允許加班與換線',
          changes: {
            product_id: formData.product_id,
            quantity: formData.quantity,
            target_date: formData.target_date,
            strategy: 'rush',
          },
        },
        {
          name: '效率優先',
          description: '最小化換線與加班成本',
          changes: {
            product_id: formData.product_id,
            quantity: formData.quantity,
            target_date: formData.target_date,
            strategy: 'efficiency',
          },
        },
      ],
      metrics: ['on_time_rate', 'utilization', 'overtime_hours', 'changeover_time', 'additional_cost', 'affected_orders'],
    }

    const data = await doSimulate(request)
    if (data) {
      setResults(data)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-amber-500" />
          <h1 className="text-2xl font-bold tracking-tight">急單模擬</h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          輸入急單資訊，模擬插單對現有排程的影響並比較不同方案
        </p>
      </div>

      {/* Simulation Form */}
      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">急單資訊</h2>
        <SimulationForm onSubmit={handleSimulate} isLoading={isLoading} />
      </div>

      {/* Results */}
      {results && <ScenarioComparison results={results} />}
    </div>
  )
}
