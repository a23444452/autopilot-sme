'use client'

import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { OrderCreate, OrderItemCreate, OrderResponse } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

interface OrderFormProps {
  /** Pre-fill for edit mode. */
  initialData?: OrderResponse | null
  onSubmit: (data: OrderCreate) => Promise<void>
  onCancel: () => void
  isLoading?: boolean
}

// ─── Component ───────────────────────────────────────────────────────────────

export function OrderForm({ initialData, onSubmit, onCancel, isLoading }: OrderFormProps) {
  const [orderNo, setOrderNo] = useState(initialData?.order_no ?? '')
  const [customerName, setCustomerName] = useState(initialData?.customer_name ?? '')
  const [dueDate, setDueDate] = useState(initialData?.due_date?.slice(0, 10) ?? '')
  const [priority, setPriority] = useState(initialData?.priority ?? 2)
  const [notes, setNotes] = useState(initialData?.notes ?? '')
  const [items, setItems] = useState<OrderItemCreate[]>(
    initialData?.items?.map((i) => ({ product_id: i.product_id, quantity: i.quantity })) ?? [
      { product_id: '', quantity: 1 },
    ],
  )
  const [error, setError] = useState<string | null>(null)

  function addItem() {
    setItems((prev) => [...prev, { product_id: '', quantity: 1 }])
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  function updateItem(index: number, field: keyof OrderItemCreate, value: string | number) {
    setItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)),
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    // Basic validation
    if (!orderNo.trim()) {
      setError('請輸入訂單編號')
      return
    }
    if (!customerName.trim()) {
      setError('請輸入客戶名稱')
      return
    }
    if (!dueDate) {
      setError('請選擇交期')
      return
    }

    const validItems = items.filter((i) => i.product_id.trim())
    if (validItems.length === 0) {
      setError('請至少新增一個品項')
      return
    }

    try {
      await onSubmit({
        order_no: orderNo.trim(),
        customer_name: customerName.trim(),
        due_date: dueDate,
        priority,
        notes: notes.trim() || null,
        items: validItems,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : '儲存失敗')
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

      {/* Basic Fields */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">訂單編號 *</label>
          <input
            type="text"
            value={orderNo}
            onChange={(e) => setOrderNo(e.target.value)}
            placeholder="例: ORD-2026-001"
            className={inputClass}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">客戶名稱 *</label>
          <input
            type="text"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            placeholder="例: 台積電"
            className={inputClass}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">交期 *</label>
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className={inputClass}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">優先順序</label>
          <select
            value={priority}
            onChange={(e) => setPriority(Number(e.target.value))}
            className={inputClass}
          >
            <option value={1}>1 - 低</option>
            <option value={2}>2 - 中</option>
            <option value={3}>3 - 高</option>
            <option value={4}>4 - 急</option>
            <option value={5}>5 - 最高</option>
          </select>
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-sm font-medium">備註</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="選填備註..."
          className={cn(inputClass, 'resize-none')}
        />
      </div>

      {/* Order Items Sub-form */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">訂單品項 *</label>
          <button
            type="button"
            onClick={addItem}
            className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
          >
            <Plus className="h-3.5 w-3.5" />
            新增品項
          </button>
        </div>

        <div className="space-y-2">
          {items.map((item, index) => (
            <div key={index} className="flex items-center gap-3">
              <input
                type="text"
                value={item.product_id}
                onChange={(e) => updateItem(index, 'product_id', e.target.value)}
                placeholder="產品 ID"
                className={cn(inputClass, 'flex-1')}
              />
              <input
                type="number"
                value={item.quantity}
                onChange={(e) => updateItem(index, 'quantity', Number(e.target.value))}
                min={1}
                className={cn(inputClass, 'w-28')}
              />
              <button
                type="button"
                onClick={() => removeItem(index)}
                disabled={items.length <= 1}
                className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-destructive disabled:opacity-40"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 border-t pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? '儲存中...' : initialData ? '更新訂單' : '建立訂單'}
        </button>
      </div>
    </form>
  )
}
