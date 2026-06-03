import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { PositionSchema } from '@/types/db'
import { z } from 'zod'

export function usePositions(podId: string) {
  return useQuery({
    queryKey: ['positions', podId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('positions')
        .select('*')
        .eq('pod_id', podId)
        .neq('quantity', 0)
        .order('market_value', { ascending: false })
      if (error) throw error
      return z.array(PositionSchema).parse(data)
    },
    enabled: !!podId,
    staleTime: 15_000,
    refetchInterval: 30_000,
  })
}
