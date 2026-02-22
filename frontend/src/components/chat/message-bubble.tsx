'use client'

import { Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  suggestions?: string[]
  timestamp: Date
}

interface MessageBubbleProps {
  message: ChatMessage
  onSuggestionClick?: (suggestion: string) => void
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Render structured content: detect markdown-like tables and confidence scores.
 */
function renderContent(content: string) {
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  let tableLines: string[] = []

  function flushTable() {
    if (tableLines.length < 2) {
      // Not a real table, render as plain text
      tableLines.forEach((line, i) => {
        elements.push(<p key={`text-${elements.length}-${i}`}>{line}</p>)
      })
      tableLines = []
      return
    }

    const headers = tableLines[0]
      .split('|')
      .map((h) => h.trim())
      .filter(Boolean)
    const dataRows = tableLines
      .slice(1)
      .filter((l) => !l.match(/^[\s|:-]+$/)) // skip separator rows
      .map((row) =>
        row
          .split('|')
          .map((c) => c.trim())
          .filter(Boolean),
      )

    elements.push(
      <div key={`table-${elements.length}`} className="my-2 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b">
              {headers.map((h, i) => (
                <th key={i} className="px-3 py-1.5 text-left font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, ri) => (
              <tr key={ri} className="border-b last:border-0">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-3 py-1.5">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>,
    )
    tableLines = []
  }

  for (const line of lines) {
    if (line.trim().startsWith('|')) {
      tableLines.push(line)
    } else {
      if (tableLines.length > 0) flushTable()

      // Confidence score rendering
      const confidenceMatch = line.match(/信心度[：:]\s*(\d+)%/i)
      if (confidenceMatch) {
        const pct = parseInt(confidenceMatch[1], 10)
        elements.push(
          <div
            key={`conf-${elements.length}`}
            className="my-1 flex items-center gap-2 text-sm"
          >
            <span className="text-muted-foreground">信心度:</span>
            <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  'h-full rounded-full',
                  pct >= 80
                    ? 'bg-green-500'
                    : pct >= 50
                      ? 'bg-amber-500'
                      : 'bg-red-500',
                )}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="font-medium">{pct}%</span>
          </div>,
        )
      } else if (line.trim()) {
        elements.push(<p key={`p-${elements.length}`}>{line}</p>)
      }
    }
  }

  if (tableLines.length > 0) flushTable()

  return elements
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Chat message bubble – renders user vs AI messages with structured data support.
 * Detects tables and confidence scores in AI responses.
 */
export function MessageBubble({ message, onSuggestionClick }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          'max-w-[75%] space-y-1 rounded-lg px-4 py-3 text-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted',
        )}
      >
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <div className="space-y-1">{renderContent(message.content)}</div>
        )}

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 border-t pt-2 text-xs text-muted-foreground">
            <span className="font-medium">來源: </span>
            {message.sources.join(', ')}
          </div>
        )}

        {/* Suggestions */}
        {!isUser && message.suggestions && message.suggestions.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 border-t pt-2">
            {message.suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSuggestionClick?.(s)}
                className="rounded-full border bg-background px-2.5 py-0.5 text-xs transition-colors hover:bg-accent"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
