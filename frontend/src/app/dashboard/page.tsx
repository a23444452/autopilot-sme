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
  isOffline: boolean
}> {
  try {
    const [jobs, productionLines, orders] = await Promise.all([
      getCurrentSchedule(),
      listProductionLines(),
      listOrders({ limit: 100 }),
    ])

    // Derive KPI metrics from jobs list
    const totalJobs = jobs.length
    const inProgressJobs = jobs.filter((j) => j.status === 'in_progress')
    const utilization = totalJobs > 0 ? inProgressJobs.length / totalJobs : 0

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
      const lineJobs = jobs.filter(
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

    // Generate alerts from at-risk orders
    const alerts: AlertItem[] = []

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
      // TODO: Trend values and qualityRate/overtimeHours are placeholders.
      // These should be calculated from backend historical data (e.g. compare current vs previous period).
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
      isOffline: false,
    }
  } catch {
    return { ...getMockDashboardData(), isOffline: true }
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
  const { kpi, lines, alerts, isOffline } = await getDashboardData()

  return (
    <div className="space-y-6">
      {/* Offline Data Banner */}
      {isOffline && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            使用離線資料
          </div>
          <p className="mt-1 text-xs text-amber-700">
            無法連線至後端服務，目前顯示的是預設範例資料。資料僅供參考，不代表實際生產狀態。
          </p>
        </div>
      )}

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
