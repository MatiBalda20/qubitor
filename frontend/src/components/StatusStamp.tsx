import { STATUS_LABEL } from '@/lib/labels'
import { cn } from '@/lib/cn'
import type { FindingStatus } from '@/types/Finding'

/**
 * Sello de estado. Un hallazgo resuelto o descartado no desaparece:
 * queda sellado, como un formulario anulado, y se puede reabrir.
 */
export function StatusStamp({ status, className }: { status: FindingStatus; className?: string }) {
  if (status === 'open') {
    return (
      <span className={cn('text-xs font-semibold tracking-[0.04em] text-ink-2 uppercase', className)}>
        {STATUS_LABEL.open}
      </span>
    )
  }
  return (
    <span
      className={cn(
        'inline-flex h-6 -rotate-2 items-center rounded-xs border-[3px] border-double px-1.5 text-[0.6875rem] leading-none font-bold tracking-[0.08em] whitespace-nowrap uppercase',
        status === 'resolved' ? 'border-ok text-ok' : 'border-stamp text-stamp',
        className,
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  )
}
