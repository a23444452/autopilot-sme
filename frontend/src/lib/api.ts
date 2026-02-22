/**
 * API client for backend communication.
 * Uses Next.js rewrites to proxy /api/* to the FastAPI backend.
 */

import type {
  ChatRequest,
  ChatResponse,
  ComplianceReport,
  DecisionLogResponse,
  HealthCheck,
  MemoryEntryResponse,
  MemorySearch,
  OrderCreate,
  OrderResponse,
  ProductCreate,
  ProductResponse,
  ProductionLineCreate,
  ProductionLineResponse,
  ScheduleRequest,
  ScheduleResult,
  SimulationRequest,
  SimulationResult,
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
}): Promise<ScheduleResult> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.production_line_id) qs.set('production_line_id', params.production_line_id)
  const query = qs.toString()
  return request<ScheduleResult>(`/schedule/current${query ? `?${query}` : ''}`)
}

// ─── Simulation ──────────────────────────────────────────────────────────────

export async function simulateRushOrder(data: SimulationRequest): Promise<SimulationResult[]> {
  return request<SimulationResult[]>('/simulate/rush-order', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function simulateDelivery(data: {
  product_id: string
  quantity: number
  target_date?: string
}): Promise<SimulationResult> {
  return request<SimulationResult>('/simulate/delivery', {
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
    method: 'PUT',
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
