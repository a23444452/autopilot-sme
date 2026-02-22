'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { ArrowUpDown, Eye } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDateShort } from '@/lib/utils'
import type { OrderResponse } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

type SortField = 'order_no' | 'customer_name' | 'due_date' | 'priority' | 'status' | 'created_at'
type SortDir = 'asc' | 'desc'

interface OrderTableProps {
  orders: OrderResponse[]
  pageSize?: number
}

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

const PRIORITY_LABELS: Record<number, string> = {
  1: '最高',
  2: '高',
  3: '中',
  4: '低',
  5: '最低',
}

// ─── Component ───────────────────────────────────────────────────────────────

export function OrderTable({ orders, pageSize = 10 }: OrderTableProps) {
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(0)

  // Filter
  const filtered = useMemo(() => {
    if (!statusFilter) return orders
    return orders.filter((o) => o.status === statusFilter)
  }, [orders, statusFilter])

  // Sort
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0
      const av = a[sortField]
      const bv = b[sortField]
      if (typeof av === 'string' && typeof bv === 'string') {
        cmp = av.localeCompare(bv)
      } else if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortField, sortDir])

  // Paginate
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const paginated = sorted.slice(page * pageSize, (page + 1) * pageSize)

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir('asc')
    }
    setPage(0)
  }

  const statuses = ['', 'pending', 'in_progress', 'completed', 'cancelled']

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-muted-foreground">狀態篩選</label>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value)
            setPage(0)
          }}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        >
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s === '' ? '全部' : STATUS_LABELS[s] ?? s}
            </option>
          ))}
        </select>
        <span className="ml-auto text-sm text-muted-foreground">
          共 {filtered.length} 筆訂單
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              {([
                ['order_no', '訂單編號'],
                ['customer_name', '客戶'],
                ['due_date', '交期'],
                ['priority', '優先順序'],
                ['status', '狀態'],
                ['created_at', '建立時間'],
              ] as [SortField, string][]).map(([field, label]) => (
                <th
                  key={field}
                  className="cursor-pointer px-4 py-3 text-left font-medium text-muted-foreground hover:text-foreground"
                  onClick={() => toggleSort(field)}
                >
                  <span className="inline-flex items-center gap-1">
                    {label}
                    <ArrowUpDown
                      className={cn(
                        'h-3.5 w-3.5',
                        sortField === field ? 'text-foreground' : 'text-muted-foreground/40',
                      )}
                    />
                  </span>
                </th>
              ))}
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">操作</th>
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                  無訂單資料
                </td>
              </tr>
            ) : (
              paginated.map((order) => (
                <tr key={order.id} className="border-b last:border-b-0 hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">{order.order_no}</td>
                  <td className="px-4 py-3">{order.customer_name}</td>
                  <td className="px-4 py-3">{formatDateShort(order.due_date)}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-block rounded px-2 py-0.5 text-xs font-medium',
                        order.priority <= 2
                          ? 'bg-red-100 text-red-800'
                          : order.priority <= 4
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-gray-100 text-gray-600',
                      )}
                    >
                      {PRIORITY_LABELS[order.priority] ?? order.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                        STATUS_COLORS[order.status] ?? 'bg-gray-100 text-gray-600',
                      )}
                    >
                      {STATUS_LABELS[order.status] ?? order.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatDateShort(order.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/orders/${order.id}`}
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      <Eye className="h-4 w-4" />
                      檢視
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            第 {page + 1} / {totalPages} 頁
          </span>
          <div className="flex gap-2">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-40"
            >
              上一頁
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-40"
            >
              下一頁
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
