'use client'

import { useState } from 'react'
import { Pencil, X, Check, Plus, Factory, Package, BookOpen } from 'lucide-react'
import { useApi, useMutation } from '@/hooks/use-api'
import {
  listProductionLines,
  updateProductionLine,
  listProducts,
  updateProduct,
  listDecisionLogs,
} from '@/lib/api'
import type {
  ProductionLineResponse,
  ProductionLineCreate,
  ProductResponse,
  ProductCreate,
  DecisionLogResponse,
} from '@/lib/types'

// ─── Tab Type ─────────────────────────────────────────────────────────────────

type TabKey = 'lines' | 'products' | 'decisions'

const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'lines', label: '產線設定', icon: <Factory className="h-4 w-4" /> },
  { key: 'products', label: '產品主檔', icon: <Package className="h-4 w-4" /> },
  { key: 'decisions', label: '決策紀錄', icon: <BookOpen className="h-4 w-4" /> },
]

// ─── Inline Edit Hook ─────────────────────────────────────────────────────────

function useInlineEdit<T extends Record<string, unknown>>() {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Partial<T>>({})

  function startEdit(id: string, initial: Partial<T>) {
    setEditingId(id)
    setDraft(initial)
  }

  function cancelEdit() {
    setEditingId(null)
    setDraft({})
  }

  function updateDraft(field: keyof T, value: unknown) {
    setDraft((prev) => ({ ...prev, [field]: value }))
  }

  return { editingId, draft, startEdit, cancelEdit, updateDraft }
}

// ─── Page Component ───────────────────────────────────────────────────────────

/**
 * Knowledge base page – displays production line configurations,
 * product master data, and learning records (decision log history).
 * Includes inline editing for production line settings and product data.
 */
export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<TabKey>('lines')

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">知識庫</h1>
        <p className="text-sm text-muted-foreground">
          產線設定、產品主檔與決策學習紀錄
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 border-b">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`inline-flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'lines' && <ProductionLinesTab />}
      {activeTab === 'products' && <ProductsTab />}
      {activeTab === 'decisions' && <DecisionLogsTab />}
    </div>
  )
}

// ─── Production Lines Tab ─────────────────────────────────────────────────────

function ProductionLinesTab() {
  const { data: lines, isLoading, error, refetch } = useApi<ProductionLineResponse[]>(
    () => listProductionLines({ limit: 200 }),
  )

  const { mutate: doUpdate } = useMutation<ProductionLineResponse, { id: string; data: Partial<ProductionLineCreate> }>(
    ({ id, data }) => updateProductionLine(id, data),
  )

  const { editingId, draft, startEdit, cancelEdit, updateDraft } = useInlineEdit<ProductionLineCreate>()

  async function handleSave(id: string) {
    const result = await doUpdate({ id, data: draft })
    if (result) {
      cancelEdit()
      await refetch()
    }
  }

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState message={error.message} />
  if (!lines?.length) return <EmptyState label="尚無產線資料" />

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-4 py-3 text-left font-medium">名稱</th>
            <th className="px-4 py-3 text-left font-medium">每小時產能</th>
            <th className="px-4 py-3 text-left font-medium">效率因子</th>
            <th className="px-4 py-3 text-left font-medium">狀態</th>
            <th className="px-4 py-3 text-left font-medium">說明</th>
            <th className="px-4 py-3 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {lines.map((line) => (
            <tr key={line.id} className="hover:bg-muted/30">
              {editingId === line.id ? (
                <>
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={(draft.name as string) ?? line.name}
                      onChange={(e) => updateDraft('name', e.target.value)}
                      className="w-full rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      value={(draft.capacity_per_hour as number) ?? line.capacity_per_hour}
                      onChange={(e) => updateDraft('capacity_per_hour', Number(e.target.value))}
                      className="w-24 rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      step="0.01"
                      value={(draft.efficiency_factor as number) ?? line.efficiency_factor}
                      onChange={(e) => updateDraft('efficiency_factor', Number(e.target.value))}
                      className="w-24 rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <select
                      value={(draft.status as string) ?? line.status}
                      onChange={(e) => updateDraft('status', e.target.value)}
                      className="rounded border px-2 py-1 text-sm"
                    >
                      <option value="active">啟用</option>
                      <option value="maintenance">維護中</option>
                      <option value="inactive">停用</option>
                    </select>
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={(draft.description as string) ?? line.description ?? ''}
                      onChange={(e) => updateDraft('description', e.target.value)}
                      className="w-full rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="inline-flex gap-1">
                      <button
                        onClick={() => handleSave(line.id)}
                        className="rounded p-1 text-green-600 hover:bg-green-50"
                        title="儲存"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="rounded p-1 text-muted-foreground hover:bg-muted"
                        title="取消"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td className="px-4 py-3 font-medium">{line.name}</td>
                  <td className="px-4 py-3">{line.capacity_per_hour}</td>
                  <td className="px-4 py-3">{line.efficiency_factor}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={line.status} />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{line.description ?? '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() =>
                        startEdit(line.id, {
                          name: line.name,
                          capacity_per_hour: line.capacity_per_hour,
                          efficiency_factor: line.efficiency_factor,
                          status: line.status,
                          description: line.description ?? '',
                        })
                      }
                      className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                      title="編輯"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Products Tab ─────────────────────────────────────────────────────────────

function ProductsTab() {
  const { data: products, isLoading, error, refetch } = useApi<ProductResponse[]>(
    () => listProducts({ limit: 200 }),
  )

  const { mutate: doUpdate } = useMutation<ProductResponse, { id: string; data: Partial<ProductCreate> }>(
    ({ id, data }) => updateProduct(id, data),
  )

  const { editingId, draft, startEdit, cancelEdit, updateDraft } = useInlineEdit<ProductCreate>()

  async function handleSave(id: string) {
    const result = await doUpdate({ id, data: draft })
    if (result) {
      cancelEdit()
      await refetch()
    }
  }

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState message={error.message} />
  if (!products?.length) return <EmptyState label="尚無產品資料" />

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-4 py-3 text-left font-medium">SKU</th>
            <th className="px-4 py-3 text-left font-medium">名稱</th>
            <th className="px-4 py-3 text-left font-medium">標準工時 (min)</th>
            <th className="px-4 py-3 text-left font-medium">換線時間 (min)</th>
            <th className="px-4 py-3 text-left font-medium">良率</th>
            <th className="px-4 py-3 text-left font-medium">學習工時</th>
            <th className="px-4 py-3 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {products.map((product) => (
            <tr key={product.id} className="hover:bg-muted/30">
              {editingId === product.id ? (
                <>
                  <td className="px-4 py-2 font-mono text-xs">{product.sku}</td>
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={(draft.name as string) ?? product.name}
                      onChange={(e) => updateDraft('name', e.target.value)}
                      className="w-full rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      step="0.1"
                      value={(draft.standard_cycle_time as number) ?? product.standard_cycle_time}
                      onChange={(e) => updateDraft('standard_cycle_time', Number(e.target.value))}
                      className="w-24 rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      step="0.1"
                      value={(draft.setup_time as number) ?? product.setup_time}
                      onChange={(e) => updateDraft('setup_time', Number(e.target.value))}
                      className="w-24 rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      value={(draft.yield_rate as number) ?? product.yield_rate}
                      onChange={(e) => updateDraft('yield_rate', Number(e.target.value))}
                      className="w-24 rounded border px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {product.learned_cycle_time != null ? `${product.learned_cycle_time} min` : '—'}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="inline-flex gap-1">
                      <button
                        onClick={() => handleSave(product.id)}
                        className="rounded p-1 text-green-600 hover:bg-green-50"
                        title="儲存"
                      >
                        <Check className="h-4 w-4" />
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="rounded p-1 text-muted-foreground hover:bg-muted"
                        title="取消"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td className="px-4 py-3 font-mono text-xs">{product.sku}</td>
                  <td className="px-4 py-3 font-medium">{product.name}</td>
                  <td className="px-4 py-3">{product.standard_cycle_time}</td>
                  <td className="px-4 py-3">{product.setup_time}</td>
                  <td className="px-4 py-3">{(product.yield_rate * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {product.learned_cycle_time != null ? `${product.learned_cycle_time} min` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() =>
                        startEdit(product.id, {
                          name: product.name,
                          standard_cycle_time: product.standard_cycle_time,
                          setup_time: product.setup_time,
                          yield_rate: product.yield_rate,
                        })
                      }
                      className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                      title="編輯"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Decision Logs Tab ────────────────────────────────────────────────────────

function DecisionLogsTab() {
  const { data: logs, isLoading, error } = useApi<DecisionLogResponse[]>(
    () => listDecisionLogs({ limit: 200 }),
  )

  if (isLoading) return <LoadingState />
  if (error) return <ErrorState message={error.message} />
  if (!logs?.length) return <EmptyState label="尚無決策紀錄" />

  return (
    <div className="space-y-4">
      {logs.map((log) => (
        <div key={log.id} className="rounded-lg border bg-card p-4 shadow-sm">
          <div className="mb-2 flex items-start justify-between">
            <div>
              <span className="inline-block rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {log.decision_type}
              </span>
              <p className="mt-1 font-medium">{log.situation}</p>
            </div>
            <div className="text-right text-xs text-muted-foreground">
              <div>{new Date(log.created_at).toLocaleString('zh-TW')}</div>
              <div>信心度: {(log.confidence * 100).toFixed(0)}%</div>
            </div>
          </div>

          {log.chosen_option && (
            <p className="text-sm">
              <span className="font-medium text-muted-foreground">選擇方案：</span>
              {log.chosen_option}
            </p>
          )}

          {log.lessons_learned && (
            <p className="mt-1 text-sm text-muted-foreground">
              <span className="font-medium">學到的教訓：</span>
              {log.lessons_learned}
            </p>
          )}

          {log.options_considered && Object.keys(log.options_considered).length > 0 && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                查看考慮的方案
              </summary>
              <pre className="mt-1 overflow-x-auto rounded bg-muted/50 p-2 text-xs">
                {JSON.stringify(log.options_considered, null, 2)}
              </pre>
            </details>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Shared UI Components ─────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    maintenance: 'bg-yellow-100 text-yellow-800',
    inactive: 'bg-gray-100 text-gray-600',
  }

  const labels: Record<string, string> = {
    active: '啟用',
    maintenance: '維護中',
    inactive: '停用',
  }

  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {labels[status] ?? status}
    </span>
  )
}

function LoadingState() {
  return <div className="py-12 text-center text-muted-foreground">載入中...</div>
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
      載入失敗: {message}
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return <div className="py-12 text-center text-muted-foreground">{label}</div>
}
