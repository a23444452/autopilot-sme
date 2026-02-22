'use client'

import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useApi, useMutation } from '@/hooks/use-api'
import { listOrders, createOrder } from '@/lib/api'
import type { OrderCreate, OrderResponse } from '@/lib/types'
import { OrderTable } from '@/components/orders/order-table'
import { OrderForm } from '@/components/orders/order-form'

// ─── Page Component ──────────────────────────────────────────────────────────

/**
 * Order management page – lists all orders with filtering/sorting
 * and allows creating new orders via a slide-in form.
 */
export default function OrdersPage() {
  const [showForm, setShowForm] = useState(false)

  const { data: orders, isLoading, error, refetch } = useApi<OrderResponse[]>(
    () => listOrders({ limit: 200 }),
  )

  const { mutate: doCreate, isLoading: isCreating } = useMutation<OrderResponse, OrderCreate>(
    (data) => createOrder(data),
  )

  async function handleCreate(data: OrderCreate) {
    const result = await doCreate(data)
    if (result) {
      setShowForm(false)
      await refetch()
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">訂單管理</h1>
          <p className="text-sm text-muted-foreground">
            檢視、建立及管理生產訂單
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            新增訂單
          </button>
        )}
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">建立新訂單</h2>
          <OrderForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
            isLoading={isCreating}
          />
        </div>
      )}

      {/* Loading / Error */}
      {isLoading && (
        <div className="py-12 text-center text-muted-foreground">載入中...</div>
      )}
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          載入訂單失敗: {error.message}
        </div>
      )}

      {/* Order Table */}
      {orders && <OrderTable orders={orders} />}
    </div>
  )
}
