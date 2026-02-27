/**
 * Shared TypeScript types mirroring backend Pydantic schemas.
 * Keep in sync with backend/app/schemas/*.py
 */

// ─── Order ───────────────────────────────────────────────────────────────────

export interface OrderItemCreate {
  product_id: string
  quantity: number
}

export interface OrderItemResponse {
  id: string
  order_id: string
  product_id: string
  quantity: number
  created_at: string
}

export interface OrderCreate {
  order_no: string
  customer_name: string
  due_date: string
  priority?: number
  notes?: string | null
  items?: OrderItemCreate[]
}

export interface OrderResponse {
  id: string
  order_no: string
  customer_name: string
  due_date: string
  priority: number
  status: string
  notes: string | null
  created_at: string
  updated_at: string
  items: OrderItemResponse[]
}

// ─── Product ─────────────────────────────────────────────────────────────────

export interface ProductCreate {
  sku: string
  name: string
  description?: string | null
  standard_cycle_time: number
  setup_time?: number
  yield_rate?: number
}

export interface ProductResponse {
  id: string
  sku: string
  name: string
  description: string | null
  standard_cycle_time: number
  setup_time: number
  yield_rate: number
  learned_cycle_time: number | null
  created_at: string
  updated_at: string
}

// ─── Production Line ─────────────────────────────────────────────────────────

export interface ProductionLineCreate {
  name: string
  description?: string | null
  capacity_per_hour: number
  efficiency_factor?: number
  status?: string
  allowed_products?: string[] | null
  changeover_matrix?: Record<string, unknown> | null
}

export interface ProductionLineResponse {
  id: string
  name: string
  description: string | null
  capacity_per_hour: number
  efficiency_factor: number
  status: string
  allowed_products: string[] | null
  changeover_matrix: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

// ─── Process Station ────────────────────────────────────────────────────────

export interface ProcessStationCreate {
  production_line_id: string
  name: string
  station_order: number
  equipment_type: string
  standard_cycle_time: number
  actual_cycle_time?: number | null
  capabilities?: Record<string, unknown> | null
  status?: string
}

export interface ProcessStationResponse {
  id: string
  production_line_id: string
  name: string
  station_order: number
  equipment_type: string
  standard_cycle_time: number
  actual_cycle_time: number | null
  capabilities: Record<string, unknown> | null
  status: string
  created_at: string
  updated_at: string
}

// ─── Process Route ──────────────────────────────────────────────────────────

export interface RouteStep {
  station_order: number
  equipment_type: string
  cycle_time_sec: number
  actual_cycle_time_sec?: number | null
}

export interface ProcessRouteCreate {
  product_id: string
  version?: number
  is_active?: boolean
  steps: RouteStep[]
  source?: 'manual' | 'spec_parsed' | 'mes_learned'
  source_file?: string | null
}

export interface ProcessRouteResponse {
  id: string
  product_id: string
  version: number
  is_active: boolean
  steps: RouteStep[]
  source: string
  source_file: string | null
  created_at: string
  updated_at: string
}

// ─── Line Capability ───────────────────────────────────────────────────────

export interface LineCapabilityCreate {
  production_line_id: string
  equipment_type: string
  capability_params?: Record<string, unknown> | null
  throughput_range?: Record<string, unknown> | null
}

export interface LineCapabilityResponse {
  id: string
  production_line_id: string
  equipment_type: string
  capability_params: Record<string, unknown> | null
  throughput_range: Record<string, unknown> | null
  updated_at: string
}

// ─── Product-Line Matching ──────────────────────────────────────────────────

export interface ProductLineMatch {
  production_line_id: string
  name: string
  matched_types: string[]
  all_types: string[]
}

// ─── Schedule ────────────────────────────────────────────────────────────────

export interface ScheduleRequest {
  order_ids?: string[]
  horizon_days?: number
  strategy?: 'balanced' | 'rush' | 'efficiency'
}

export interface ScheduledJobResponse {
  id: string
  order_item_id: string
  production_line_id: string
  product_id: string
  planned_start: string
  planned_end: string
  quantity: number
  changeover_time: number
  status: string
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ScheduleResult {
  jobs: ScheduledJobResponse[]
  total_jobs: number
  total_changeover_minutes: number
  utilization_pct: number
  warnings: string[]
  metadata: Record<string, unknown>
}

// ─── Simulation ──────────────────────────────────────────────────────────────

export interface Scenario {
  name: string
  description?: string | null
  changes: Record<string, unknown>
}

export interface SimulationRequest {
  base_schedule_id?: string | null
  scenarios: Scenario[]
  metrics?: string[]
}

export interface SimulationResult {
  scenario_name: string
  metrics: Record<string, number>
  comparison: Record<string, unknown>
  warnings: string[]
  metadata: Record<string, unknown>
}

export interface RushOrderRequest {
  product_id: string
  quantity: number
  target_date: string
  priority?: number
}

export interface RushOrderSimulationResponse {
  scenarios: RushOrderScenario[]
  rush_order: Record<string, unknown>
  recommended_scenario: string | null
  total_scenarios: number
}

export interface RushOrderScenario {
  name: string
  description: string
  production_line_id: string
  production_line_name: string
  completion_time: string
  changeover_time: number
  production_hours: number
  affected_orders: {
    order_item_id: string
    original_end: string
    new_end: string
    delay_minutes: number
  }[]
  overtime_hours: number
  additional_cost: number
  meets_target: boolean
  recommendation: boolean
  warnings: string[]
}

export interface DeliveryEstimateRequest {
  product_id: string
  quantity: number
}

export interface DeliveryEstimateResponse {
  product_id: string
  quantity: number
  estimated_completion: string
  confidence: number
  earliest: string
  latest: string
  notes: string[]
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export interface ChatRequest {
  message: string
  conversation_id?: string | null
  context?: Record<string, unknown>
}

export interface ChatResponse {
  reply: string
  conversation_id: string
  sources: string[]
  suggestions: string[]
  metadata: Record<string, unknown>
}

// ─── Memory ──────────────────────────────────────────────────────────────────

export interface MemorySearch {
  query: string
  memory_type?: 'structured' | 'episodic' | 'semantic' | null
  category?: string | null
  limit?: number
}

export interface MemoryEntryResponse {
  id: string
  memory_type: string
  category: string
  content: string
  metadata: Record<string, unknown> | null
  importance: number
  lifecycle: string
  access_count: number
  last_accessed_at: string | null
  created_at: string
  updated_at: string
}

export interface DecisionLogResponse {
  id: string
  decision_type: string
  situation: string
  context: Record<string, unknown> | null
  options_considered: Record<string, unknown> | null
  chosen_option: string | null
  outcome: Record<string, unknown> | null
  lessons_learned: string | null
  confidence: number
  created_at: string
}

// ─── Compliance ──────────────────────────────────────────────────────────────

export interface UsageStats {
  total_calls: number
  total_tokens: number
  total_cost_usd: number
  avg_latency_ms: number
  calls_by_provider: Record<string, number>
  calls_by_task_type: Record<string, number>
  error_rate: number
  period_start: string | null
  period_end: string | null
}

export interface ComplianceReport {
  report_id: string
  generated_at: string
  period_start: string
  period_end: string
  usage_stats: UsageStats
  model_breakdown: Record<string, unknown>[]
  policy_violations: string[]
  recommendations: string[]
}

// ─── Common ──────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export interface HealthCheck {
  status: string
}
