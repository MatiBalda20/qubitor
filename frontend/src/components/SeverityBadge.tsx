import { SEVERITY_LABEL } from '@/lib/labels'
import { cn } from '@/lib/cn'
import { SEVERITY_STYLES } from '@/lib/severityStyles'
import type { Severity } from '@/types/Finding'

/** Marcas de nivel: la severidad se lee también sin color. */
const LEVEL: Record<Severity, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 }

interface SeverityBadgeProps {
  severity: Severity
  size?: 'sm' | 'md'
  className?: string
}

export function SeverityBadge({ severity, size = 'md', className }: SeverityBadgeProps) {
  const level = LEVEL[severity]
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-xs font-semibold uppercase ring-1 ring-inset',
        size === 'sm' ? 'h-5 px-1.5 text-[0.625rem] tracking-[0.06em]' : 'h-6 px-2 text-[0.6875rem] tracking-[0.06em]',
        SEVERITY_STYLES[severity].badge,
        className,
      )}
    >
      <span aria-hidden="true" className="flex items-end gap-px">
        {[1, 2, 3, 4].map((step) => (
          <span
            key={step}
            className={cn('w-[2px] rounded-[1px] bg-current', step > level && 'opacity-25')}
            style={{ height: `${3 + step * 1.5}px` }}
          />
        ))}
      </span>
      {SEVERITY_LABEL[severity]}
    </span>
  )
}
