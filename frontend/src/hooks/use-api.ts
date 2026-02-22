'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * State shape for API calls managed by useApi hook.
 */
export interface UseApiState<T> {
  data: T | null
  error: Error | null
  isLoading: boolean
}

/**
 * Return type for useApi hook.
 */
export interface UseApiReturn<T> extends UseApiState<T> {
  refetch: () => Promise<void>
}

/**
 * Custom hook for declarative API calls with loading/error/data states
 * and refetch capability.
 *
 * @param fetcher - Async function that returns data of type T.
 * @param options - Configuration options.
 * @param options.enabled - Whether to auto-fetch on mount (default: true).
 * @param options.deps - Additional dependencies that trigger a refetch.
 *
 * @example
 * ```tsx
 * const { data, isLoading, error, refetch } = useApi(() => listOrders())
 * ```
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  options: {
    enabled?: boolean
    deps?: unknown[]
  } = {},
): UseApiReturn<T> {
  const { enabled = true, deps = [] } = options

  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    error: null,
    isLoading: enabled,
  })

  // Track whether the component is still mounted to avoid state updates
  // after unmount.
  const mountedRef = useRef(true)
  useEffect(() => {
    return () => {
      mountedRef.current = false
    }
  }, [])

  // Stable reference to the fetcher to avoid re-triggering on every render.
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const execute = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }))

    try {
      const data = await fetcherRef.current()
      if (mountedRef.current) {
        setState({ data, error: null, isLoading: false })
      }
    } catch (err) {
      if (mountedRef.current) {
        setState({
          data: null,
          error: err instanceof Error ? err : new Error(String(err)),
          isLoading: false,
        })
      }
    }
  }, [])

  // Auto-fetch on mount and when deps change.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (enabled) {
      execute()
    }
  }, [enabled, execute, ...deps])

  return {
    ...state,
    refetch: execute,
  }
}

/**
 * Hook for imperative (mutation) API calls that don't auto-fetch.
 *
 * @param mutator - Async function that accepts args and returns data.
 *
 * @example
 * ```tsx
 * const { mutate, isLoading, error, data } = useMutation(
 *   (order: OrderCreate) => createOrder(order)
 * )
 * await mutate(newOrder)
 * ```
 */
export function useMutation<TData, TArgs = void>(
  mutator: (args: TArgs) => Promise<TData>,
): {
  mutate: (args: TArgs) => Promise<TData | null>
  data: TData | null
  error: Error | null
  isLoading: boolean
  reset: () => void
} {
  const [state, setState] = useState<UseApiState<TData>>({
    data: null,
    error: null,
    isLoading: false,
  })

  const mountedRef = useRef(true)
  useEffect(() => {
    return () => {
      mountedRef.current = false
    }
  }, [])

  const mutatorRef = useRef(mutator)
  mutatorRef.current = mutator

  const mutate = useCallback(async (args: TArgs): Promise<TData | null> => {
    setState({ data: null, error: null, isLoading: true })

    try {
      const data = await mutatorRef.current(args)
      if (mountedRef.current) {
        setState({ data, error: null, isLoading: false })
      }
      return data
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      if (mountedRef.current) {
        setState({ data: null, error, isLoading: false })
      }
      return null
    }
  }, [])

  const reset = useCallback(() => {
    setState({ data: null, error: null, isLoading: false })
  }, [])

  return {
    mutate,
    ...state,
    reset,
  }
}
