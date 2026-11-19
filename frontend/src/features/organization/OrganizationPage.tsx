import { OrganizationSwitcher, useOrganization } from '@clerk/clerk-react'
import { Check, Minus, RefreshCw, ServerCrash } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/layout/PageHeader'
import { Skeleton } from '@/components/Loader'
import { cn } from '@/lib/cn'
import { AUTH_ENABLED, USE_MOCKS } from '@/lib/config'
import { formatDateTime, pluralize } from '@/lib/format'
import { loadOrganization, type Me, type Member, type MemberRole, type OrganizationData } from './dataSource'

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: OrganizationData }

const ROLE_LABEL: Record<MemberRole, string> = { admin: 'Admin', member: 'Miembro' }

const PERMISSIONS: readonly { key: keyof Me['permissions']; label: string }[] = [
  { key: 'connect_repositories', label: 'Conectar repositorios' },
  { key: 'start_scans', label: 'Lanzar escaneos' },
  { key: 'update_findings', label: 'Marcar hallazgos como resueltos o falsos positivos' },
]

/** Vista «Organización» (Módulo A): rol del usuario, permisos y miembros. */
export default function OrganizationPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  const load = useCallback(async () => {
    setState({ status: 'loading' })
    try {
      setState({ status: 'ready', data: await loadOrganization() })
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : 'Error desconocido.' })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <>
      <PageHeader
        title="Organización"
        meta={
          state.status === 'ready' ? (
            <span className="flex flex-wrap gap-x-2 gap-y-1">
              <span>{state.data.me.organization.personal ? 'Tu espacio personal' : state.data.me.organization.name}</span>
              <span className="tabular">
                <span aria-hidden="true" className="mr-2">·</span>
                {pluralize(state.data.members.length, 'miembro', 'miembros')}
              </span>
            </span>
          ) : undefined
        }
      />
      <div className="space-y-5 px-4 pb-12 sm:px-8">
        {USE_MOCKS && (
          <p className="text-xs text-ink-3">
            Datos de ejemplo de <code className="font-mono">features/organization/mock.json</code>: la API todavía no está conectada.
          </p>
        )}
        <OrganizationControls onChange={load} />
        {state.status === 'loading' && <OrganizationSkeleton />}
        {state.status === 'error' && (
          <div className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
            <EmptyState
              icon={ServerCrash}
              tone="error"
              title="No pudimos cargar la organización"
              description={state.message}
              action={
                <button
                  type="button"
                  onClick={load}
                  className="inline-flex h-10 items-center gap-2 rounded-sm bg-civic px-4 text-sm font-semibold text-civic-ink hover:bg-civic-deep active:scale-[0.96]"
                >
                  <RefreshCw className="size-4" strokeWidth={2} aria-hidden="true" />
                  Reintentar
                </button>
              }
            />
          </div>
        )}
        {state.status === 'ready' && (
          <div className="grid grid-cols-[minmax(0,1fr)] gap-5 xl:grid-cols-12">
            <RoleSheet me={state.data.me} className="xl:col-span-5" />
            <MembersSheet members={state.data.members} className="xl:col-span-7" />
          </div>
        )}
      </div>
    </>
  )
}

/**
 * Crear organizaciones, cambiar de organización, invitar miembros y cambiar
 * roles se hace con los componentes de Clerk: Clerk es la fuente de verdad de
 * los roles y la API los lee del token en cada pedido.
 */
function OrganizationControls({ onChange }: { onChange: () => void }) {
  if (!AUTH_ENABLED) {
    return (
      <p className="max-w-[75ch] text-sm text-ink-2">
        En modo demo no hay organizaciones de Clerk. Con login, desde acá se crean organizaciones, se cambia de
        organización y se invita a los miembros.
      </p>
    )
  }
  return <ClerkControls onChange={onChange} />
}

function ClerkControls({ onChange }: { onChange: () => void }) {
  const { organization, isLoaded } = useOrganization()
  const current = organization?.id ?? null
  const previous = useRef<string | null | undefined>(undefined)

  // Al cambiar de organización en Clerk cambia el token: se vuelven a pedir los datos.
  useEffect(() => {
    if (!isLoaded) return
    if (previous.current !== undefined && previous.current !== current) onChange()
    previous.current = current
  }, [current, isLoaded, onChange])

  return (
    <section aria-labelledby="org-switch-title" className="rounded-sm bg-sheet px-5 py-4 shadow-sheet ring-1 ring-rule">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 max-w-[60ch]">
          <h2 id="org-switch-title" className="text-base font-semibold text-ink">
            Organización activa
          </h2>
          <p className="mt-1 text-sm text-ink-2">
            Los repositorios y escaneos son de la organización activa. Para invitar miembros o cambiar roles, abrí el
            menú y entrá a «Administrar».
          </p>
        </div>
        <OrganizationSwitcher
          afterSelectOrganizationUrl="/organization"
          afterSelectPersonalUrl="/organization"
          afterCreateOrganizationUrl="/organization"
          appearance={{ elements: { organizationSwitcherTrigger: 'rounded-sm ring-1 ring-rule-2 px-3 py-2' } }}
        />
      </div>
    </section>
  )
}

function RoleSheet({ me, className }: { me: Me; className?: string }) {
  return (
    <section aria-labelledby="role-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="role-title" className="text-base font-semibold text-ink">
          Tu rol
        </h2>
        <RoleTag role={me.role} />
      </header>
      <div className="px-5 py-4">
        <p className="max-w-[75ch] text-sm text-ink-2">
          {me.organization.personal
            ? 'En tu espacio personal sos admin: podés hacer todo.'
            : me.role === 'admin'
              ? 'Como admin podés hacer todo, incluido conectar repositorios a la organización.'
              : 'Como miembro podés ver todo, lanzar escaneos y gestionar hallazgos. Conectar repositorios lo hace un admin.'}
        </p>
        <dl className="mt-4 divide-y divide-rule">
          {PERMISSIONS.map(({ key, label }) => {
            const allowed = me.permissions[key]
            return (
              <div key={key} className="flex items-center justify-between gap-4 py-2.5 text-sm">
                <dt className="text-ink">{label}</dt>
                <dd className={cn('inline-flex items-center gap-1.5 font-medium', allowed ? 'text-ok' : 'text-ink-3')}>
                  {allowed ? (
                    <Check className="size-4" strokeWidth={2} aria-hidden="true" />
                  ) : (
                    <Minus className="size-4" strokeWidth={2} aria-hidden="true" />
                  )}
                  {allowed ? 'Sí' : 'No'}
                </dd>
              </div>
            )
          })}
        </dl>
      </div>
    </section>
  )
}

function MembersSheet({ members, className }: { members: readonly Member[]; className?: string }) {
  return (
    <section aria-labelledby="members-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="members-title" className="text-base font-semibold text-ink">
          Miembros
        </h2>
        <p className="text-xs text-ink-3">Los que ya entraron a Qubitor en esta organización</p>
      </header>
      <ul className="divide-y divide-rule">
        {members.map((member) => (
          <li key={member.user_id} className="flex items-center gap-3 px-5 py-3">
            <Avatar member={member} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ink">
                {member.name ?? 'Usuario sin nombre'}
                {member.is_you && <span className="ml-1.5 font-normal text-ink-3">(vos)</span>}
              </p>
              <p className="truncate text-xs text-ink-3 tabular">
                {member.last_seen_at ? `Última actividad: ${formatDateTime(member.last_seen_at)}` : 'Sin actividad registrada'}
              </p>
            </div>
            <RoleTag role={member.role} />
          </li>
        ))}
      </ul>
    </section>
  )
}

function RoleTag({ role }: { role: MemberRole }) {
  return (
    <span
      className={cn(
        'inline-flex h-6 shrink-0 items-center rounded-xs px-2 text-xs font-semibold tracking-[0.04em] uppercase ring-1 ring-inset',
        role === 'admin' ? 'bg-civic-soft text-civic ring-civic/20' : 'bg-sheet text-ink-2 ring-rule-2',
      )}
    >
      {ROLE_LABEL[role]}
    </span>
  )
}

function Avatar({ member }: { member: Member }) {
  if (member.image_url) {
    return <img src={member.image_url} alt="" className="size-9 shrink-0 rounded-full object-cover ring-1 ring-rule" />
  }
  const initials = (member.name ?? '?')
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
  return (
    <span aria-hidden="true" className="grid size-9 shrink-0 place-items-center rounded-full bg-paper text-xs font-semibold text-ink-2 ring-1 ring-rule">
      {initials || '?'}
    </span>
  )
}

function OrganizationSkeleton() {
  return (
    <div role="status" aria-label="Cargando la organización" className="grid grid-cols-[minmax(0,1fr)] gap-5 xl:grid-cols-12">
      <Skeleton className="h-56 xl:col-span-5" />
      <Skeleton className="h-56 xl:col-span-7" />
    </div>
  )
}
