import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: ReactNode
  /** Botón o enlace con la acción que destraba la pantalla. */
  action?: ReactNode
  tone?: 'neutral' | 'error'
  className?: string
}

/** Estado vacío o de error: dice qué pasa y qué hacer a continuación. */
export function EmptyState({ icon: Icon, title, description, action, tone = 'neutral', className }: EmptyStateProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : undefined}
      className={cn('t-reveal flex flex-col items-center px-6 py-12 text-center', className)}
    >
      {Icon && (
        <span
          className={cn(
            'mb-4 grid size-11 place-items-center rounded-sm ring-1',
            tone === 'error'
              ? 'bg-sev-critical-soft text-sev-critical ring-sev-critical/25'
              : 'bg-civic-soft text-civic ring-civic/15',
          )}
        >
          <Icon className="size-5" strokeWidth={1.75} aria-hidden="true" />
        </span>
      )}
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {description && <p className="mt-1.5 max-w-[46ch] text-sm text-ink-2">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
