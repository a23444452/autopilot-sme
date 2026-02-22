'use client'

import { useState, useMemo } from 'react'
import { ArrowUpDown } from 'lucide-react'
import { cn, formatDate, formatDuration } from '@/lib/utils'
import type { ScheduledJobResponse } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

type SortField = 'planned_start' | 'planned_end' | 'production_line_id' | 'product_id' | 'quantity' | 'status'
type SortDir = 'asc' | 'desc'

interface ScheduleTableProps {
  jobs: ScheduledJobResponse[]
  pageSize?: number
}

// ─── Status Helpers ──────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  scheduled: '已排程',
  in_progress: '生產中',
  completed: '已完成',
  cancelled: '已取消',
  pending: '待處理',
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-amber-100 text-amber-800',
  completed: 'bg-emerald-100 text-emerald-800',
  cancelled: 'bg-gray-100 text-gray-600',
  pending: 'bg-purple-100 text-purple-800',
}

// ─── Component ───────────────────────────────────────────────────────────────

export function ScheduleTable({ jobs, pageSize = 15 }: ScheduleTableProps) {
  const [sortField, setSortField] = useState<SortField>('planned_start')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(0)

  // Sort
  const sorted = useMemo(() => {
    return [...jobs].sort((a, b) => {
      const av = a[sortField]
      const bv = b[sortField]
      let cmp = 0
      if (typeof av === 'string' && typeof bv === 'string') {
        cmp = av.localeCompare(bv)
      } else if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [jobs, sortField, sortDir])

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

  return (
    <div className="space-y-4">
      <span className="text-sm text-muted-foreground">
        共 {jobs.length} 筆排程工作
      </span>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              {([
                ['planned_start', '計劃開始'],
                ['planned_end', '計劃結束'],
                ['production_line_id', '產線'],
                ['product_id', '產品'],
                ['quantity', '數量'],
                ['status', '狀態'],
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
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">換線時間</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">備註</th>
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                  尚無排程資料
                </td>
              </tr>
            ) : (
              paginated.map((job) => (
                <tr key={job.id} className="border-b last:border-b-0 hover:bg-muted/30">
                  <td className="px-4 py-3">{formatDate(job.planned_start)}</td>
                  <td className="px-4 py-3">{formatDate(job.planned_end)}</td>
                  <td className="px-4 py-3 font-medium">{job.production_line_id.slice(0, 8)}</td>
                  <td className="px-4 py-3">{job.product_id.slice(0, 8)}</td>
                  <td className="px-4 py-3 text-right">{job.quantity.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                        STATUS_COLORS[job.status] ?? 'bg-gray-100 text-gray-600',
                      )}
                    >
                      {STATUS_LABELS[job.status] ?? job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatDuration(job.changeover_time)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {job.notes ?? '-'}
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
