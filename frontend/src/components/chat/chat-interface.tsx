'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { useMutation } from '@/hooks/use-api'
import { sendChatMessage } from '@/lib/api'
import type { ChatRequest, ChatResponse } from '@/lib/types'
import { MessageBubble, type ChatMessage } from './message-bubble'
import { QuickActions } from './quick-actions'

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Chat interface managing conversation state, API calls, and message rendering.
 * Handles message history, auto-scroll, and input submission.
 */
export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const { mutate: send, isLoading } = useMutation<ChatResponse, ChatRequest>(
    (data) => sendChatMessage(data),
  )

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || isLoading) return

      // Add user message
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setInput('')

      // Send to API
      const response = await send({
        message: trimmed,
        conversation_id: conversationId,
      })

      if (response) {
        setConversationId(response.conversation_id)
        const assistantMsg: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.reply,
          sources: response.sources,
          suggestions: response.suggestions,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])
      }
    },
    [conversationId, isLoading, send],
  )

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    handleSend(input)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(input)
    }
  }

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col rounded-lg border bg-card shadow-sm">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-6">
            <div className="text-center">
              <p className="text-lg font-medium">歡迎使用 AI 助手</p>
              <p className="mt-1 text-sm text-muted-foreground">
                選擇快速操作或直接輸入問題開始對話
              </p>
            </div>
            <QuickActions onSelect={handleSend} disabled={isLoading} />
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onSuggestionClick={handleSend}
              />
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
                <div className="rounded-lg bg-muted px-4 py-3 text-sm text-muted-foreground">
                  思考中...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 border-t p-4"
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="輸入問題，例如：本週有哪些訂單即將到期？"
          rows={1}
          disabled={isLoading}
          className="flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </form>
    </div>
  )
}
