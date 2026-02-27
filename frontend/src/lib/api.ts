/**
 * API client for backend communication.
 * Uses Next.js rewrites to proxy /api/* to the FastAPI backend.
 */

import type {
  ChatRequest,
  ChatResponse,
  ComplianceReport,
  DecisionLogResponse,
  DeliveryEstimateRequest,
  DeliveryEstimateResponse,
  HealthCheck,
  LineCapabilityCreate,
  LineCapabilityResponse,
  MemoryEntryResponse,
  MemorySearch,
  OrderCreate,
  OrderResponse,
  ProcessRouteCreate,
  ProcessRouteResponse,
  ProcessStationCreate,
  ProcessStationResponse,
  ProductCreate,
  ProductLineMatch,
  ProductResponse,
  ProductionLineCreate,
  ProductionLineResponse,
  RushOrderRequest,
  RushOrderSimulationResponse,
  ScheduleRequest,
  ScheduleResult,
  ScheduledJobResponse,
  UsageStats,
} from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api/v1'

// ─── Fetch Wrapper ───────────────────────────────────────────────────────────

class ApiClientError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiClientError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`

  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!res.ok) {
    let detail = `Request failed: ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // ignore parse errors
    }
    throw new ApiClientError(res.status, detail)
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T
  }

  return res.json() as Promise<T>
}

// ─── Health ──────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthCheck> {
  return request<HealthCheck>('/health')
}

// ─── Orders ──────────────────────────────────────────────────────────────────

export async function listOrders(params?: {
  status?: string
  due_date_from?: string
  due_date_to?: string
  skip?: number
  limit?: number
}): Promise<OrderResponse[]> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.due_date_from) qs.set('due_date_from', params.due_date_from)
  if (params?.due_date_to) qs.set('due_date_to', params.due_date_to)
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<OrderResponse[]>(`/orders${query ? `?${query}` : ''}`)
}

export async function getOrder(id: string): Promise<OrderResponse> {
  return request<OrderResponse>(`/orders/${id}`)
}

export async function createOrder(data: OrderCreate): Promise<OrderResponse> {
  return request<OrderResponse>('/orders', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateOrder(id: string, data: Partial<OrderCreate>): Promise<OrderResponse> {
  return request<OrderResponse>(`/orders/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteOrder(id: string): Promise<void> {
  return request<void>(`/orders/${id}`, { method: 'DELETE' })
}

// ─── Products ────────────────────────────────────────────────────────────────

export async function listProducts(params?: {
  skip?: number
  limit?: number
}): Promise<ProductResponse[]> {
  const qs = new URLSearchParams()
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<ProductResponse[]>(`/products${query ? `?${query}` : ''}`)
}

export async function getProduct(id: string): Promise<ProductResponse> {
  return request<ProductResponse>(`/products/${id}`)
}

export async function createProduct(data: ProductCreate): Promise<ProductResponse> {
  return request<ProductResponse>('/products', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProduct(id: string, data: Partial<ProductCreate>): Promise<ProductResponse> {
  return request<ProductResponse>(`/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProduct(id: string): Promise<void> {
  return request<void>(`/products/${id}`, { method: 'DELETE' })
}

// ─── Production Lines ────────────────────────────────────────────────────────

export async function listProductionLines(params?: {
  status?: string
  skip?: number
  limit?: number
}): Promise<ProductionLineResponse[]> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<ProductionLineResponse[]>(`/production-lines${query ? `?${query}` : ''}`)
}

export async function getProductionLine(id: string): Promise<ProductionLineResponse> {
  return request<ProductionLineResponse>(`/production-lines/${id}`)
}

export async function createProductionLine(data: ProductionLineCreate): Promise<ProductionLineResponse> {
  return request<ProductionLineResponse>('/production-lines', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProductionLine(id: string, data: Partial<ProductionLineCreate>): Promise<ProductionLineResponse> {
  return request<ProductionLineResponse>(`/production-lines/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProductionLine(id: string): Promise<void> {
  return request<void>(`/production-lines/${id}`, { method: 'DELETE' })
}

// ─── Process Stations ───────────────────────────────────────────────────────

export async function listStations(params?: {
  production_line_id?: string
  skip?: number
  limit?: number
}): Promise<ProcessStationResponse[]> {
  const qs = new URLSearchParams()
  if (params?.production_line_id) qs.set('production_line_id', params.production_line_id)
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<ProcessStationResponse[]>(`/stations${query ? `?${query}` : ''}`)
}

export async function getStation(id: string): Promise<ProcessStationResponse> {
  return request<ProcessStationResponse>(`/stations/${id}`)
}

export async function createStation(data: ProcessStationCreate): Promise<ProcessStationResponse> {
  return request<ProcessStationResponse>('/stations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateStation(id: string, data: ProcessStationCreate): Promise<ProcessStationResponse> {
  return request<ProcessStationResponse>(`/stations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteStation(id: string): Promise<void> {
  return request<void>(`/stations/${id}`, { method: 'DELETE' })
}

// ─── Process Routes ─────────────────────────────────────────────────────────

export async function listProcessRoutes(params?: {
  product_id?: string
  active_only?: boolean
  skip?: number
  limit?: number
}): Promise<ProcessRouteResponse[]> {
  const qs = new URLSearchParams()
  if (params?.product_id) qs.set('product_id', params.product_id)
  if (params?.active_only) qs.set('active_only', 'true')
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<ProcessRouteResponse[]>(`/process-routes${query ? `?${query}` : ''}`)
}

export async function getProcessRoute(id: string): Promise<ProcessRouteResponse> {
  return request<ProcessRouteResponse>(`/process-routes/${id}`)
}

export async function createProcessRoute(data: ProcessRouteCreate): Promise<ProcessRouteResponse> {
  return request<ProcessRouteResponse>('/process-routes', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProcessRoute(id: string, data: ProcessRouteCreate): Promise<ProcessRouteResponse> {
  return request<ProcessRouteResponse>(`/process-routes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProcessRoute(id: string): Promise<void> {
  return request<void>(`/process-routes/${id}`, { method: 'DELETE' })
}

// ─── Line Capabilities ─────────────────────────────────────────────────────

export async function listLineCapabilities(params?: {
  production_line_id?: string
  skip?: number
  limit?: number
}): Promise<LineCapabilityResponse[]> {
  const qs = new URLSearchParams()
  if (params?.production_line_id) qs.set('production_line_id', params.production_line_id)
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<LineCapabilityResponse[]>(`/line-capabilities${query ? `?${query}` : ''}`)
}

export async function createLineCapability(data: LineCapabilityCreate): Promise<LineCapabilityResponse> {
  return request<LineCapabilityResponse>('/line-capabilities', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteLineCapability(id: string): Promise<void> {
  return request<void>(`/line-capabilities/${id}`, { method: 'DELETE' })
}

// ─── Product-Line Matching ──────────────────────────────────────────────────

export async function matchProductToLines(params: {
  product_id: string
  equipment_types: string[]
}): Promise<ProductLineMatch[]> {
  const qs = new URLSearchParams()
  qs.set('product_id', params.product_id)
  for (const t of params.equipment_types) {
    qs.append('equipment_types', t)
  }
  return request<ProductLineMatch[]>(`/matching/product-lines?${qs.toString()}`)
}

// ─── Schedule ────────────────────────────────────────────────────────────────

export async function generateSchedule(data: ScheduleRequest): Promise<ScheduleResult> {
  return request<ScheduleResult>('/schedule/generate', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getCurrentSchedule(params?: {
  status?: string
  production_line_id?: string
  skip?: number
  limit?: number
}): Promise<ScheduledJobResponse[]> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.production_line_id) qs.set('production_line_id', params.production_line_id)
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<ScheduledJobResponse[]>(`/schedule/current${query ? `?${query}` : ''}`)
}

// ─── Simulation ──────────────────────────────────────────────────────────────

export async function simulateRushOrder(data: RushOrderRequest): Promise<RushOrderSimulationResponse> {
  return request<RushOrderSimulationResponse>('/simulate/rush-order', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function simulateDelivery(data: DeliveryEstimateRequest): Promise<DeliveryEstimateResponse> {
  return request<DeliveryEstimateResponse>('/simulate/delivery', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export async function sendChatMessage(data: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ─── Memory ──────────────────────────────────────────────────────────────────

export async function searchMemories(data: MemorySearch): Promise<MemoryEntryResponse[]> {
  return request<MemoryEntryResponse[]>('/memory/search', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function listFacts(params?: {
  memory_type?: string
  category?: string
  lifecycle?: string
  skip?: number
  limit?: number
}): Promise<MemoryEntryResponse[]> {
  const qs = new URLSearchParams()
  if (params?.memory_type) qs.set('memory_type', params.memory_type)
  if (params?.category) qs.set('category', params.category)
  if (params?.lifecycle) qs.set('lifecycle', params.lifecycle)
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<MemoryEntryResponse[]>(`/memory/facts${query ? `?${query}` : ''}`)
}

export async function createFact(data: {
  memory_type: string
  category: string
  content: string
  metadata?: Record<string, unknown>
  importance?: number
}): Promise<MemoryEntryResponse> {
  return request<MemoryEntryResponse>('/memory/facts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ─── Compliance ──────────────────────────────────────────────────────────────

export async function getUsageStats(params?: {
  period_start?: string
  period_end?: string
}): Promise<UsageStats> {
  const qs = new URLSearchParams()
  if (params?.period_start) qs.set('period_start', params.period_start)
  if (params?.period_end) qs.set('period_end', params.period_end)
  const query = qs.toString()
  return request<UsageStats>(`/compliance/usage${query ? `?${query}` : ''}`)
}

export async function listDecisionLogs(params?: {
  decision_type?: string
  skip?: number
  limit?: number
}): Promise<DecisionLogResponse[]> {
  const qs = new URLSearchParams()
  if (params?.decision_type) qs.set('decision_type', params.decision_type)
  if (params?.skip != null) qs.set('skip', String(params.skip))
  if (params?.limit != null) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return request<DecisionLogResponse[]>(`/compliance/decisions${query ? `?${query}` : ''}`)
}

export { ApiClientError }
