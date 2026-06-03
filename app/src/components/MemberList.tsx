import { useMembers } from '@/hooks/useMembers'
import type { Member } from '@/types/db'

interface MemberListProps {
  podId: string
}

function Avatar({ member }: { member: Member }) {
  if (member.avatar_url) {
    return (
      <img
        src={member.avatar_url}
        alt={member.name}
        className="w-8 h-8 rounded-full object-cover"
      />
    )
  }
  const initials = member.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
  return (
    <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white">
      {initials}
    </div>
  )
}

export function MemberList({ podId }: MemberListProps) {
  const { data: members, isLoading } = useMembers(podId)

  if (isLoading) {
    return (
      <div className="flex gap-3 animate-pulse">
        {[0, 1, 2].map((i) => (
          <div key={i} className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-white/10" />
        ))}
      </div>
    )
  }

  const pm = members?.find((m) => m.role === 'pm')
  const traders = members?.filter((m) => m.role === 'trader') ?? []

  return (
    <div className="flex flex-wrap gap-4 text-sm">
      {pm && (
        <div className="flex items-center gap-2">
          <Avatar member={pm} />
          <div>
            <p className="font-medium text-zinc-900 dark:text-white">{pm.name}</p>
            <p className="text-xs text-indigo-600 dark:text-indigo-400 uppercase tracking-wide">PM</p>
          </div>
        </div>
      )}
      {traders.map((t) => (
        <div key={t.id} className="flex items-center gap-2">
          <Avatar member={t} />
          <div>
            <p className="font-medium text-zinc-900 dark:text-white">{t.name}</p>
            <p className="text-xs text-zinc-500 uppercase tracking-wide">Trader</p>
          </div>
        </div>
      ))}
    </div>
  )
}
