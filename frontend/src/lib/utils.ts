import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge Tailwind CSS classes with conflict resolution.
 * Combines clsx (conditional classes) with tailwind-merge (dedup).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ─── Date Formatting ─────────────────────────────────────────────────────────

/**
 * Format an ISO date string to localized display format (Traditional Chinese).
 * Example: "2026-03-15T08:00:00Z" → "2026/03/15 08:00"
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return '-'
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

/**
 * Format a date to short date only (no time).
 * Example: "2026-03-15T08:00:00Z" → "2026/03/15"
 */
export function formatDateShort(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return '-'
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/**
 * Format a date to relative time (e.g., "3 天前", "2 小時後").
 */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return '-'

  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  const absDiffMs = Math.abs(diffMs)
  const suffix = diffMs < 0 ? '前' : '後'

  const minutes = Math.floor(absDiffMs / 60_000)
  if (minutes < 60) return `${minutes} 分鐘${suffix}`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小時${suffix}`

  const days = Math.floor(hours / 24)
  return `${days} 天${suffix}`
}

// ─── Number Formatting ───────────────────────────────────────────────────────

/**
 * Format a number as percentage string.
 * Example: 0.953 → "95.3%"
 */
export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '-'
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * Format a number with locale-aware grouping.
 * Example: 12345.6 → "12,345.6"
 */
export function formatNumber(value: number | null | undefined, decimals?: number): string {
  if (value == null) return '-'
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/**
 * Format USD currency.
 * Example: 12.5 → "$12.50"
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return '-'
  return `$${value.toFixed(2)}`
}

/**
 * Format minutes to human-readable duration.
 * Example: 135 → "2 小時 15 分鐘"
 */
export function formatDuration(minutes: number | null | undefined): string {
  if (minutes == null) return '-'
  if (minutes < 60) return `${Math.round(minutes)} 分鐘`
  const hrs = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (mins === 0) return `${hrs} 小時`
  return `${hrs} 小時 ${mins} 分鐘`
}
