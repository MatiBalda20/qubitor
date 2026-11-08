import { UserButton, useUser } from '@clerk/clerk-react'
import { FlaskConical } from 'lucide-react'
import { AUTH_ENABLED } from '@/lib/config'

/** Usuario actual al pie del menú lateral, o el aviso de modo demo. */
export function UserMenu() {
  return AUTH_ENABLED ? <ClerkUser /> : <DemoUser />
}

function ClerkUser() {
  const { user } = useUser()
  return (
    <div className="flex items-center gap-3 px-2 py-1.5">
      <UserButton appearance={{ elements: { avatarBox: 'size-8' } }} />
      <div className="min-w-0 text-sm">
        <p className="truncate font-semibold">{user?.fullName ?? user?.username ?? 'Tu cuenta'}</p>
        <p className="truncate text-xs text-civic-muted">{user?.primaryEmailAddress?.emailAddress}</p>
      </div>
    </div>
  )
}

function DemoUser() {
  return (
    <div className="flex items-center gap-3 rounded-sm px-2 py-1.5">
      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-white/12">
        <FlaskConical className="size-4" strokeWidth={1.75} aria-hidden="true" />
      </span>
      <div className="min-w-0 text-sm">
        <p className="font-semibold">Modo demo</p>
        <p className="truncate text-xs text-civic-muted">Datos de ejemplo, sin login</p>
      </div>
    </div>
  )
}
