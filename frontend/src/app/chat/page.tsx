'use client'

import { MessageSquare } from 'lucide-react'
import { ChatInterface } from '@/components/chat/chat-interface'

// ─── Page Component ──────────────────────────────────────────────────────────

/**
 * AI Chat page – conversational interface for querying scheduling data,
 * simulating rush orders, and generating reports via natural language.
 */
export default function ChatPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">AI 對話</h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          透過自然語言查詢排程資訊、模擬急單、生成報表
        </p>
      </div>

      {/* Chat Interface */}
      <ChatInterface />
    </div>
  )
}
