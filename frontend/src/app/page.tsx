'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Home page – redirects to /dashboard.
 * Uses client-side redirect so the sidebar active state updates correctly.
 */
export default function Home() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/dashboard')
  }, [router])

  return null
}
