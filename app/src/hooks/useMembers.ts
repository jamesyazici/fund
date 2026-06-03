import { useQuery } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { MemberSchema } from '@/types/db'
import { z } from 'zod'

export function useMembers(podId?: string) {
  return useQuery({
    queryKey: ['members', podId],
    queryFn: async () => {
      let query = supabase.from('members').select('*').order('role').order('name')
      if (podId) query = query.eq('pod_id', podId)
      const { data, error } = await query
      if (error) throw error
      return z.array(MemberSchema).parse(data)
    },
    staleTime: 300_000,
  })
}
