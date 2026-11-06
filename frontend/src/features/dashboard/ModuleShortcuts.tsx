import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { MODULE_VIEWS, type ModuleView } from '@/lib/labels'
import { SEVERITY_STYLES } from '@/lib/severityStyles'
import { SEVERITIES, type Severity } from '@/types/Finding'

interface ModuleShortcutsProps {
  /** Hallazgos abiertos por vista y severidad. */
  counts: Record<ModuleView, Record<Severity, number>>
  className?: string
}

/** Accesos directos a la vista de cada módulo, con sus hallazgos abiertos. */
export function ModuleShortcuts({ counts, className }: ModuleShortcutsProps) {
  return (
    <nav aria-labelledby="shortcuts-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="border-b border-rule px-5 py-3.5">
        <h2 id="shortcuts-title" className="text-base font-semibold text-ink">
          Vistas por área
        </h2>
      </header>
      <ul className="group/list divide-y divide-rule">
        {MODULE_VIEWS.map((view) => {
          const row = counts[view.id]
          const open = SEVERITIES.reduce((sum, s) => sum + row[s], 0)
          return (
            <li
              key={view.id}
              className="transition-opacity duration-200 group-hover/list:opacity-45 hover:!opacity-100 focus-within:!opacity-100"
            >
              <Link
                to={view.path}
                className="group flex items-center gap-4 px-5 py-3 transition-colors duration-150 hover:bg-civic-soft/50"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-ink">{view.label}</p>
                  <p className="truncate text-xs text-ink-3">{view.scope}</p>
                  <SeverityStrip counts={row} total={open} />
                </div>
                <p className="text-right">
                  <span className="block font-display text-2xl leading-none font-semibold text-ink tabular">{open}</span>
                  <span className="text-[0.6875rem] text-ink-3">abiertos</span>
                </p>
                <ArrowRight
                  className="size-4 shrink-0 text-ink-3 transition-[translate,color] duration-200 ease-(--ease-swift) group-hover:translate-x-0.5 group-hover:text-civic"
                  aria-hidden="true"
                />
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

/** Barra segmentada por severidad; decorativa, el número ya está al costado. */
function SeverityStrip({ counts, total }: { counts: Record<Severity, number>; total: number }) {
  return (
    <div aria-hidden="true" className="mt-2 flex h-1.5 gap-px overflow-hidden rounded-full bg-paper">
      {total > 0 &&
        SEVERITIES.filter((s) => counts[s] > 0).map((severity) => (
          <span
            key={severity}
            className={cn('h-full transition-[flex-grow] duration-700 ease-(--ease-swift)', SEVERITY_STYLES[severity].bar)}
            style={{ flexGrow: counts[severity] }}
          />
        ))}
    </div>
  )
}
