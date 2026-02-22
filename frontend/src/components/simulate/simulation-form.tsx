'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SimulationFormData {
  product_id: string
  quantity: number
  target_date: string
}

interface SimulationFormProps {
  onSubmit: (data: SimulationFormData) => Promise<void>
  isLoading?: boolean
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Rush order simulation input form – collects product, quantity, and target
 * delivery date for what-if analysis.
 */
export function SimulationForm({ onSubmit, isLoading }: SimulationFormProps) {
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState(100)
  const [targetDate, setTargetDate] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!productId.trim()) {
      setError('請選擇產品')
      return
    }
    if (quantity <= 0) {
      setError('數量必須大於 0')
      return
    }
    if (!targetDate) {
      setError('請選擇目標交期')
      return
    }

    try {
      await onSubmit({
        product_id: productId.trim(),
        quantity,
        target_date: targetDate,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : '模擬失敗')
    }
  }

  const inputClass =
    'w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50'

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">產品 ID *</label>
          <input
            type="text"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            placeholder="例: P001"
            className={inputClass}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">數量 *</label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
            min={1}
            className={inputClass}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">目標交期 *</label>
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            className={inputClass}
          />
        </div>
      </div>

      <div className="flex items-center justify-end">
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? '模擬中...' : '開始模擬'}
        </button>
      </div>
    </form>
  )
}
