import { UsageChart } from '@/components/compliance/usage-chart'
import type { UsageStats } from '@/lib/types'
import { DecisionLogTable } from '@/components/compliance/decision-log-table'
import type { DecisionLogResponse } from '@/lib/types'
import { getUsageStats, listDecisionLogs } from '@/lib/api'

// ─── Data Fetching ────────────────────────────────────────────────────────────

/**
 * Fetch compliance data from the backend.
 * Falls back to mock data if the API is unavailable (dev mode).
 */
async function getComplianceData(): Promise<{
  stats: UsageStats
  decisions: DecisionLogResponse[]
}> {
  try {
    const [stats, decisions] = await Promise.all([
      getUsageStats(),
      listDecisionLogs({ limit: 100 }),
    ])
    return { stats, decisions }
  } catch {
    return getMockComplianceData()
  }
}

function getMockComplianceData(): {
  stats: UsageStats
  decisions: DecisionLogResponse[]
} {
  return {
    stats: {
      total_calls: 1247,
      total_tokens: 3_842_500,
      total_cost_usd: 48.72,
      avg_latency_ms: 1250,
      calls_by_provider: {
        anthropic: 523,
        openai: 412,
        ollama: 312,
      },
      calls_by_task_type: {
        scheduling: 456,
        chat: 389,
        optimization: 234,
        analysis: 168,
      },
      error_rate: 0.023,
      period_start: '2026-02-01T00:00:00Z',
      period_end: '2026-02-22T23:59:59Z',
    },
    decisions: [
      {
        id: 'dec-001',
        decision_type: 'scheduling',
        situation: '訂單 ORD-2026-042 與 ORD-2026-045 產線衝突，需要重新排程',
        context: { conflicting_orders: 2, affected_lines: ['A線', 'B線'] },
        options_considered: { option_a: '延後 ORD-045', option_b: '分割 ORD-042 至兩條產線' },
        chosen_option: '分割 ORD-042 至兩條產線',
        outcome: { result: 'success', delay_reduced_hours: 4 },
        lessons_learned: '大型訂單分割可有效降低交期風險',
        confidence: 0.87,
        created_at: '2026-02-22T14:30:00Z',
      },
      {
        id: 'dec-002',
        decision_type: 'model_selection',
        situation: '使用者查詢需要多語言理解能力，評估最適合的模型',
        context: { language: 'zh-TW', complexity: 'high' },
        options_considered: { claude: 'claude-sonnet-4-6', gpt: 'gpt-4.1' },
        chosen_option: 'claude-sonnet-4-6',
        outcome: { quality_score: 0.94, latency_ms: 1100 },
        lessons_learned: 'Claude 在繁體中文理解上表現較優',
        confidence: 0.92,
        created_at: '2026-02-22T10:15:00Z',
      },
      {
        id: 'dec-003',
        decision_type: 'fallback',
        situation: 'Anthropic API 回傳 529 過載錯誤，需要備援切換',
        context: { error_code: 529, retry_count: 2 },
        options_considered: { retry: '重試 Anthropic', fallback: '切換至 OpenAI' },
        chosen_option: '切換至 OpenAI',
        outcome: { result: 'success', fallback_latency_ms: 800 },
        lessons_learned: '529 錯誤應直接切換，避免等待重試',
        confidence: 0.95,
        created_at: '2026-02-21T16:45:00Z',
      },
      {
        id: 'dec-004',
        decision_type: 'optimization',
        situation: '產線 B 稼動率低於 70%，建議最佳化排程',
        context: { current_utilization: 0.65, target: 0.85 },
        options_considered: { rebalance: '重新平衡產線負載', consolidate: '合併小批次訂單' },
        chosen_option: '重新平衡產線負載',
        outcome: { new_utilization: 0.82, improvement_pct: 26 },
        lessons_learned: '平衡負載比合併訂單效果更好',
        confidence: 0.78,
        created_at: '2026-02-21T09:00:00Z',
      },
    ],
  }
}

// ─── Page Component ───────────────────────────────────────────────────────────

/**
 * Compliance dashboard page – Server Component that fetches usage statistics
 * and decision audit logs for AI governance and transparency.
 */
export default async function CompliancePage() {
  const { stats, decisions } = await getComplianceData()

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">合規儀表板</h1>
        <p className="text-sm text-muted-foreground">
          AI 使用統計與決策審計紀錄
        </p>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <p className="text-sm font-medium text-muted-foreground">總呼叫次數</p>
          <p className="mt-1 text-2xl font-bold tracking-tight">
            {stats.total_calls.toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <p className="text-sm font-medium text-muted-foreground">總 Token 用量</p>
          <p className="mt-1 text-2xl font-bold tracking-tight">
            {(stats.total_tokens / 1_000_000).toFixed(2)}M
          </p>
        </div>
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <p className="text-sm font-medium text-muted-foreground">總花費</p>
          <p className="mt-1 text-2xl font-bold tracking-tight">
            ${stats.total_cost_usd.toFixed(2)}
          </p>
        </div>
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <p className="text-sm font-medium text-muted-foreground">錯誤率</p>
          <p className="mt-1 text-2xl font-bold tracking-tight">
            {(stats.error_rate * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Usage Charts */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">使用分佈</h2>
        <UsageChart stats={stats} />
      </div>

      {/* Decision Audit Log */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">決策審計紀錄</h2>
        <DecisionLogTable logs={decisions} />
      </div>
    </div>
  )
}
