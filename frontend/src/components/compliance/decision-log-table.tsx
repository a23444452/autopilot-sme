'use client'

import { useState, useMemo, useCallback } from 'react'
import { ArrowUpDown, Download } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDate } from '@/lib/utils'
import type { DecisionLogResponse } from '@/lib/types'

// ─── Types ────────────────────────────────────────────────────────────────────

type SortField = 'decision_type' | 'confidence' | 'created_at'
type SortDir = 'asc' | 'desc'

interface DecisionLogTableProps {
  logs: DecisionLogResponse[]
  pageSize?: number
}

// ─── Decision Type Labels ───────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  scheduling: '排程決策',
  model_selection: '模型選擇',
  fallback: '備援切換',
  optimization: '最佳化',
}

const TYPE_COLORS: Record<string, string> = {
  scheduling: 'bg-blue-100 text-blue-800',
  model_selection: 'bg-violet-100 text-violet-800',
  fallback: 'bg-amber-100 text-amber-800',
  optimization: 'bg-emerald-100 text-emerald-800',
}

// ─── Export Utility ─────────────────────────────────────────────────────────

function exportToCsv(logs: DecisionLogResponse[]) {
  const headers = ['ID', '類型', '情境', '選擇', '信心度', '教訓', '時間']
  const rows = logs.map((log) => [
    log.id,
    TYPE_LABELS[log.decision_type] ?? log.decision_type,
    log.situation,
    log.chosen_option ?? '-',
    `${(log.confidence * 100).toFixed(0)}%`,
    log.lessons_learned ?? '-',
    log.created_at,
  ])

  const csv = [headers, ...rows].map((row) =>
    row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','),
  ).join('\n')

  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `decision-log-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Decision log table with sorting, filtering, pagination, and CSV export.
 * Shows the AI decision audit trail for compliance tracking.
 */
export function DecisionLogTable({ logs, pageSize = 10 }: DecisionLogTableProps) {
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(0)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // Get unique decision types for filter
  const decisionTypes = useMemo(
    () => Array.from(new Set(logs.map((l) => l.decision_type))),
    [logs],
  )

  // Filter
  const filtered = useMemo(() => {
    if (!typeFilter) return logs
    return logs.filter((l) => l.decision_type === typeFilter)
  }, [logs, typeFilter])

  // Sort
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sortField === 'confidence') {
        cmp = a.confidence - b.confidence
      } else if (sortField === 'created_at') {
        cmp = a.created_at.localeCompare(b.created_at)
      } else {
        cmp = a[sortField].localeCompare(b[sortField])
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortField, sortDir])

  // Paginate
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const paginated = sorted.slice(page * pageSize, (page + 1) * pageSize)

  const toggleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
        return prev
      }
      setSortDir('asc')
      return field
    })
    setPage(0)
  }, [])

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-muted-foreground">類型篩選</label>
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value)
            setPage(0)
          }}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        >
          <option value="">全部</option>
          {decisionTypes.map((t) => (
            <option key={t} value={t}>
              {TYPE_LABELS[t] ?? t}
            </option>
          ))}
        </select>
        <span className="text-sm text-muted-foreground">
          共 {filtered.length} 筆紀錄
        </span>
        <button
          onClick={() => exportToCsv(filtered)}
          className="ml-auto inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
        >
          <Download className="h-3.5 w-3.5" />
          匯出 CSV
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              {([
                ['decision_type', '決策類型'],
                ['created_at', '時間'],
                ['confidence', '信心度'],
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
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">情境</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">選擇</th>
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  尚無決策紀錄
                </td>
              </tr>
            ) : (
              paginated.map((log) => (
                <tr
                  key={log.id}
                  className="cursor-pointer border-b last:border-b-0 hover:bg-muted/30"
                  onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                >
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                        TYPE_COLORS[log.decision_type] ?? 'bg-gray-100 text-gray-600',
                      )}
                    >
                      {TYPE_LABELS[log.decision_type] ?? log.decision_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatDate(log.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-16 overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn(
                            'h-full rounded-full',
                            log.confidence >= 0.8
                              ? 'bg-emerald-500'
                              : log.confidence >= 0.5
                                ? 'bg-amber-500'
                                : 'bg-destructive',
                          )}
                          style={{ width: `${log.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {(log.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="max-w-[200px] truncate px-4 py-3">{log.situation}</td>
                  <td className="px-4 py-3">{log.chosen_option ?? '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Expanded Detail */}
      {expandedId && (() => {
        const log = paginated.find((l) => l.id === expandedId)
        if (!log) return null
        return (
          <div className="rounded-lg border bg-muted/30 p-4 text-sm">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <p className="font-medium text-muted-foreground">完整情境</p>
                <p className="mt-1">{log.situation}</p>
              </div>
              {log.lessons_learned && (
                <div>
                  <p className="font-medium text-muted-foreground">學習教訓</p>
                  <p className="mt-1">{log.lessons_learned}</p>
                </div>
              )}
              {log.options_considered && (
                <div>
                  <p className="font-medium text-muted-foreground">考慮選項</p>
                  <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-xs">
                    {JSON.stringify(log.options_considered, null, 2)}
                  </pre>
                </div>
              )}
              {log.outcome && (
                <div>
                  <p className="font-medium text-muted-foreground">結果</p>
                  <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-xs">
                    {JSON.stringify(log.outcome, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )
      })()}

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
