import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: ReactNode
  /** Línea de contexto bajo el título (repo, rama, fecha…). */
  meta?: ReactNode
  /** Acciones alineadas a la derecha. */
  actions?: ReactNode
}

/** Encabezado común de cada vista. */
export function PageHeader({ title, meta, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 px-4 pt-7 pb-6 sm:px-8 sm:pt-9">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-[-0.01em] text-ink sm:text-[1.75rem]">{title}</h1>
        {meta && <div className="mt-1.5 text-sm text-ink-2">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  )
}
