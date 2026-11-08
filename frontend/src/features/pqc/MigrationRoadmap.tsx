import { ShieldCheck } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { SeverityBadge } from '@/components/SeverityBadge'
import { cn } from '@/lib/cn'
import type { MigrationStep } from './quantum'

/** Pasos para migrar a criptografía post-cuántica, de lo más urgente a lo menos. */
export function MigrationRoadmap({ steps, className }: { steps: readonly MigrationStep[]; className?: string }) {
  return (
    <section aria-labelledby="roadmap-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="roadmap-title" className="text-base font-semibold text-ink">
          Hoja de ruta de migración
        </h2>
        <p className="text-xs text-ink-3">De lo más urgente a lo menos</p>
      </header>

      {steps.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="Nada que migrar por ahora"
          description="No se encontró criptografía vulnerable a una computadora cuántica en este repositorio."
        />
      ) : (
        <ol className="divide-y divide-rule">
          {steps.map((step, index) => (
            <li key={step.id} className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3 px-5 py-4">
              <span className="font-display text-2xl leading-none font-semibold text-ink-3 tabular">{index + 1}</span>
              <div className="min-w-0 space-y-2">
                <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
                  <SeverityBadge severity={step.priority} size="sm" />
                  <h3 className="font-semibold text-ink">{step.title}</h3>
                </div>
                <dl className="text-sm">
                  <dt className="field-label">Migrar a</dt>
                  <dd className="font-medium text-ink">{step.target}</dd>
                </dl>
                <p className="max-w-[75ch] text-sm text-ink-2">{step.why}</p>
                <ul aria-label="Dónde se usa" className="flex flex-wrap gap-1.5">
                  {step.usages.map((usage) => (
                    <li
                      key={usage.finding.id}
                      className="rounded-xs bg-paper px-1.5 py-0.5 font-mono text-xs text-ink-2 ring-1 ring-rule ring-inset"
                    >
                      {usage.location} · {usage.algorithm}
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
