'use client'
import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/store/auth'

export type StreamEvent = {
  type: 'application' | 'connected' | string
  status?: string
  job?: { id: string; title: string; company: string; portal: string }
  ts?: number
}

type Handler = (event: StreamEvent) => void

/**
 * Connects to GET /api/v1/events/stream (SSE) and calls onEvent for each
 * message. Auto-reconnects with exponential backoff on disconnect.
 */
export function useEventStream(onEvent: Handler) {
  const token      = useAuthStore((s) => s.token)
  const esRef      = useRef<EventSource | null>(null)
  const retryDelay = useRef(1000)

  const connect = useCallback(() => {
    if (!token) return
    if (esRef.current) esRef.current.close()

    const url = `${process.env.NEXT_PUBLIC_API_URL}/events/stream`
    // EventSource doesn't support custom headers — pass token as query param
    const es = new EventSource(`${url}?token=${token}`)
    esRef.current = es

    es.onopen = () => {
      retryDelay.current = 1000 // reset backoff on successful connect
    }

    es.addEventListener('connected', (e) => {
      onEvent({ type: 'connected', ...JSON.parse(e.data) })
    })

    es.addEventListener('application', (e) => {
      onEvent({ type: 'application', ...JSON.parse(e.data) })
    })

    es.onerror = () => {
      es.close()
      esRef.current = null
      // Exponential backoff: 1s → 2s → 4s → … → 30s max
      const delay = Math.min(retryDelay.current, 30000)
      retryDelay.current = delay * 2
      setTimeout(connect, delay)
    }
  }, [token, onEvent])

  useEffect(() => {
    connect()
    return () => {
      esRef.current?.close()
      esRef.current = null
    }
  }, [connect])
}
