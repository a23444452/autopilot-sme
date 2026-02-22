'use client'

import { useParams, useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react'
import { useApi, useMutation } from '@/hooks/use-api'
import { getOrder, updateOrder, deleteOrder } from '@/lib/api'
import { formatDate, formatDateShort } from '@/lib/utils'
import type { OrderCreate, OrderResponse } from '@/lib/types'
import { OrderForm } from '@/components/orders/order-form'

// ─── Status Helpers ──────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  pending: '待處理',
  in_progress: '生產中',
  completed: '已完成',
  cancelled: '已取消',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  in_progress: 'bg-blue-100 text-blue-800',
  completed: 'bg-emerald-100 text-emerald-800',
  cancelled: 'bg-gray-100 text-gray-600',
}

// ─── Page Component ──────────────────────────────────────────────────────────

/**
 * Order detail page – shows full order info with items,
 * and allows editing or deleting the order.
 */
export default function OrderDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const [editing, setEditing] = useState(false)

  const { data: order, isLoading, error, refetch } = useApi<OrderResponse>(
    () => getOrder(params.id),
    { deps: [params.id] },
  )

  const { mutate: doUpdate, isLoading: isUpdating } = useMutation<OrderResponse, Partial<OrderCreate>>(
    (data) => updateOrder(params.id, data),
  )

  const { mutate: doDelete, isLoading: isDeleting } = useMutation<void, void>(
    () => deleteOrder(params.id),
  )

  async function handleUpdate(data: OrderCreate) {
    const result = await doUpdate(data)
    if (result) {
      setEditing(false)
      await refetch()
    }
  }

  async function handleDelete() {
    if (!confirm('確定要刪除此訂單嗎？')) return
    await doDelete(undefined as unknown as void)
    router.push('/orders')
  }

  if (isLoading) {
    return <div className="py-12 text-center text-muted-foreground">載入中...</div>
  }

  if (error) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => router.push('/orders')}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回訂單列表
        </button>
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          載入訂單失敗: {error.message}
        </div>
      </div>
    )
  }

  if (!order) return null

  return (
    <div className="space-y-6">
      {/* Back + Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push('/orders')}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回訂單列表
        </button>
        {!editing && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
            >
              <Pencil className="h-3.5 w-3.5" />
              編輯
            </button>
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="inline-flex items-center gap-1.5 rounded-md border border-destructive/50 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {isDeleting ? '刪除中...' : '刪除'}
            </button>
          </div>
        )}
      </div>

      {/* Edit Form */}
      {editing ? (
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">編輯訂單</h2>
          <OrderForm
            initialData={order}
            onSubmit={handleUpdate}
            onCancel={() => setEditing(false)}
            isLoading={isUpdating}
          />
        </div>
      ) : (
        <>
          {/* Order Header */}
          <div className="rounded-lg border bg-card p-6 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">{order.order_no}</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  客戶: {order.customer_name}
                </p>
              </div>
              <span
                className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${STATUS_COLORS[order.status] ?? 'bg-gray-100 text-gray-600'}`}
              >
                {STATUS_LABELS[order.status] ?? order.status}
              </span>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground">交期</p>
                <p className="text-sm font-medium">{formatDateShort(order.due_date)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">優先順序</p>
                <p className="text-sm font-medium">{order.priority}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">建立時間</p>
                <p className="text-sm font-medium">{formatDate(order.created_at)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">更新時間</p>
                <p className="text-sm font-medium">{formatDate(order.updated_at)}</p>
              </div>
            </div>

            {order.notes && (
              <div className="mt-4 border-t pt-4">
                <p className="text-xs text-muted-foreground">備註</p>
                <p className="mt-1 text-sm">{order.notes}</p>
              </div>
            )}
          </div>

          {/* Order Items */}
          <div className="rounded-lg border bg-card p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">訂單品項</h2>
            {order.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">無品項資料</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">#</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">產品 ID</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">數量</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">建立時間</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.items.map((item, idx) => (
                      <tr key={item.id} className="border-b last:border-b-0">
                        <td className="px-4 py-3 text-muted-foreground">{idx + 1}</td>
                        <td className="px-4 py-3 font-medium">{item.product_id}</td>
                        <td className="px-4 py-3">{item.quantity}</td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {formatDate(item.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
