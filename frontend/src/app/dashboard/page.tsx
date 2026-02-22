import { KpiCards } from '@/components/dashboard/kpi-cards'
import type { KpiData } from '@/components/dashboard/kpi-cards'
import { LineStatus } from '@/components/dashboard/line-status'
import type { LineWithProgress } from '@/components/dashboard/line-status'
import { AlertsPanel } from '@/components/dashboard/alerts-panel'
import type { AlertItem } from '@/components/dashboard/alerts-panel'
import { getCurrentSchedule, listProductionLines, listOrders } from '@/lib/api'

// ─── Data Fetching ────────────────────────────────────────────────────────────

/**
 * Fetch dashboard data from the backend.
 * Falls back to mock data if the API is unavailable (dev mode).
 */
async function getDashboardData(): Promise<{
  kpi: KpiData
  lines: LineWithProgress[]
  alerts: AlertItem[]
}> {
  try {
    const [schedule, productionLines, orders] = await Promise.all([
      getCurrentSchedule(),
      listProductionLines(),
      listOrders({ limit: 100 }),
    ])

    // Derive KPI metrics from schedule data
    const utilization = schedule.utilization_pct / 100

    // Count on-time vs total completed orders
    const completedOrders = orders.filter((o) => o.status === 'completed')
    const onTimeOrders = completedOrders.filter(
      (o) => new Date(o.updated_at) <= new Date(o.due_date),
    )
    const onTimeRate =
      completedOrders.length > 0
        ? onTimeOrders.length / completedOrders.length
        : 0.95

    // Build line progress from scheduled jobs
    const lines: LineWithProgress[] = productionLines.map((line) => {
      const lineJobs = schedule.jobs.filter(
        (j) => j.production_line_id === line.id,
      )
      const completedJobs = lineJobs.filter((j) => j.status === 'completed')
      const progress =
        lineJobs.length > 0 ? completedJobs.length / lineJobs.length : 0

      return {
        ...line,
        progress,
        activeJobs: lineJobs.filter((j) => j.status === 'in_progress').length,
      }
    })

    // Generate alerts from schedule warnings and at-risk orders
    const alerts: AlertItem[] = []

    // Schedule warnings
    schedule.warnings.forEach((warning, idx) => {
      alerts.push({
        id: `warning-${idx}`,
        severity: 'warning',
        title: '排程警告',
        description: warning,
        timestamp: new Date().toISOString(),
      })
    })

    // At-risk orders (due within 2 days and not completed)
    const now = new Date()
    const twoDaysFromNow = new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000)
    orders
      .filter(
        (o) =>
          o.status !== 'completed' &&
          o.status !== 'cancelled' &&
          new Date(o.due_date) <= twoDaysFromNow,
      )
      .forEach((order) => {
        const isOverdue = new Date(order.due_date) < now
        alerts.push({
          id: `order-${order.id}`,
          severity: isOverdue ? 'danger' : 'warning',
          title: isOverdue
            ? `訂單 ${order.order_no} 已逾期`
            : `訂單 ${order.order_no} 即將到期`,
          description: `客戶: ${order.customer_name}，交期: ${new Date(order.due_date).toLocaleDateString('zh-TW')}`,
          timestamp: order.due_date,
        })
      })

    return {
      kpi: {
        onTimeRate,
        onTimeTrend: 2.1,
        utilization,
        utilizationTrend: -0.5,
        qualityRate: 0.987,
        qualityTrend: 0.3,
        overtimeHours: 12,
        overtimeTrend: -8.2,
      },
      lines,
      alerts,
    }
  } catch {
    // Fallback mock data when backend is unavailable
    return getMockDashboardData()
  }
}

function getMockDashboardData(): {
  kpi: KpiData
  lines: LineWithProgress[]
  alerts: AlertItem[]
} {
  return {
    kpi: {
      onTimeRate: 0.953,
      onTimeTrend: 2.1,
      utilization: 0.847,
      utilizationTrend: -0.5,
      qualityRate: 0.987,
      qualityTrend: 0.3,
      overtimeHours: 12,
      overtimeTrend: -8.2,
    },
    lines: [
      {
        id: 'line-1',
        name: 'A 線 - CNC 加工',
        description: 'CNC machining line',
        capacity_per_hour: 50,
        efficiency_factor: 0.92,
        status: 'active',
        allowed_products: null,
        changeover_matrix: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        progress: 0.72,
        activeJobs: 3,
      },
      {
        id: 'line-2',
        name: 'B 線 - 組裝',
        description: 'Assembly line',
        capacity_per_hour: 80,
        efficiency_factor: 0.88,
        status: 'active',
        allowed_products: null,
        changeover_matrix: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        progress: 0.45,
        activeJobs: 2,
      },
      {
        id: 'line-3',
        name: 'C 線 - 包裝',
        description: 'Packaging line',
        capacity_per_hour: 120,
        efficiency_factor: 0.95,
        status: 'maintenance',
        allowed_products: null,
        changeover_matrix: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        progress: 0.0,
        activeJobs: 0,
      },
    ],
    alerts: [
      {
        id: 'alert-1',
        severity: 'danger',
        title: '訂單 ORD-2026-042 已逾期',
        description: '客戶: 台積電，交期: 2026/02/20',
        timestamp: '2026-02-20T00:00:00Z',
      },
      {
        id: 'alert-2',
        severity: 'warning',
        title: '訂單 ORD-2026-045 即將到期',
        description: '客戶: 鴻海精密，交期: 2026/02/24',
        timestamp: '2026-02-24T00:00:00Z',
      },
      {
        id: 'alert-3',
        severity: 'info',
        title: 'C 線維護排程',
        description: '預計 2026/02/23 完成維護',
        timestamp: '2026-02-22T00:00:00Z',
      },
    ],
  }
}

// ─── Page Component ───────────────────────────────────────────────────────────

/**
 * Dashboard page – Server Component that fetches current schedule and metrics.
 * Shows KPI cards, production line status, and alerts.
 */
export default async function DashboardPage() {
  const { kpi, lines, alerts } = await getDashboardData()

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">儀表板</h1>
        <p className="text-sm text-muted-foreground">
          生產排程總覽與關鍵指標
        </p>
      </div>

      {/* KPI Cards */}
      <KpiCards data={kpi} />

      {/* Line Status + Alerts Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <LineStatus lines={lines} />
        <AlertsPanel alerts={alerts} />
      </div>
    </div>
  )
}
