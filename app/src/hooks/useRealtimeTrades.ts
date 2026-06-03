import { useEffect, useId } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'

export function useRealtimeTrades(podId?: string) {
  const queryClient = useQueryClient()
  const uid = useId()

  useEffect(() => {
    const channel = supabase
      .channel(`trades-${podId ?? 'all'}-${uid}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'trades',
          ...(podId ? { filter: `pod_id=eq.${podId}` } : {}),
        },
        () => {
          queryClient.invalidateQueries({ queryKey: ['trades'] })
        },
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [podId, queryClient, uid])
}

export function useRealtimePositions(podId: string) {
  const queryClient = useQueryClient()
  const uid = useId()

  useEffect(() => {
    const channel = supabase
      .channel(`positions-${podId}-${uid}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'positions', filter: `pod_id=eq.${podId}` },
        () => {
          queryClient.invalidateQueries({ queryKey: ['positions', podId] })
        },
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [podId, queryClient, uid])
}

export function useRealtimeNav(podId: string) {
  const queryClient = useQueryClient()
  const uid = useId()

  useEffect(() => {
    const channel = supabase
      .channel(`nav-${podId}-${uid}`)
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'nav_history', filter: `pod_id=eq.${podId}` },
        () => {
          queryClient.invalidateQueries({ queryKey: ['nav_history', podId] })
        },
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [podId, queryClient, uid])
}
