'use client'

import { useEffect } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface ErrorPageProps {
  error: Error & { digest?: string }
  reset: () => void
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // TODO: Integrate error reporting service (e.g. Sentry) for production monitoring
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>

        <h2 className="mb-2 text-xl font-semibold">發生錯誤</h2>
        <p className="mb-6 text-sm text-muted-foreground">
          頁面載入時發生非預期的錯誤，請嘗試重新載入。
          {error.digest && (
            <span className="mt-1 block text-xs text-muted-foreground/60">
              錯誤代碼: {error.digest}
            </span>
          )}
        </p>

        <div className="flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <RefreshCw className="h-4 w-4" />
            重新載入
          </button>
          <a
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-muted"
          >
            回到儀表板
          </a>
        </div>
      </div>
    </div>
  )
}
