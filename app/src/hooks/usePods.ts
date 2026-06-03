import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { PodSchema } from '@/types/db'
import { z } from 'zod'

export function usePods() {
  return useQuery({
    queryKey: ['pods'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('pods')
        .select('*')
        .order('created_at')
      if (error) throw error
      return z.array(PodSchema).parse(data)
    },
    staleTime: 60_000,
  })
}

export function usePod(id: string) {
  return useQuery({
    queryKey: ['pods', id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('pods')
        .select('*')
        .eq('id', id)
        .single()
      if (error) throw error
      return PodSchema.parse(data)
    },
    enabled: !!id,
    staleTime: 60_000,
  })
}
