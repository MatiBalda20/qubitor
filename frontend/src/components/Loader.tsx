import { cn } from '@/lib/cn'

interface LoaderProps {
  /** Texto que se anuncia y se muestra junto al indicador. */
  label?: string
  className?: string
}

/** Indicador de carga en línea. Para bloques enteros usar <Skeleton>. */
export function Loader({ label = 'Cargando…', className }: LoaderProps) {
  return (
    <div role="status" className={cn('inline-flex items-center gap-2.5 text-sm text-ink-2', className)}>
      <svg viewBox="0 0 20 20" className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true">
        <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2.5" />
        <path d="M18 10a8 8 0 0 0-8-8" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
      <span>{label}</span>
    </div>
  )
}

/** Bloque placeholder que pulsa mientras carga (receta skeleton de transitions.dev). */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('t-skeleton', className)} />
}
