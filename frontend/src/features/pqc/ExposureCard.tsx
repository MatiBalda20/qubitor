import { cn } from '@/lib/cn'
import { SEVERITY_STYLES } from '@/lib/severityStyles'
import { THREAT_LABEL, THREAT_SEVERITY, THREATS, type ExposureSummary } from './quantum'

/** Qué parte del uso criptográfico rompería una computadora cuántica. */
export function ExposureCard({ summary, className }: { summary: ExposureSummary; className?: string }) {
  return (
    <section aria-labelledby="exposure-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="border-b border-rule px-5 py-3.5">
        <h2 id="exposure-title" className="text-base font-semibold text-ink">
          Exposición cuántica
        </h2>
      </header>

      <div className="space-y-5 px-5 py-5">
        <div>
          <p className="field-label">Vulnerable a Shor</p>
          <p className="mt-1 font-display text-5xl leading-none font-semibold text-ink tabular">{summary.shorPercent}%</p>
          <p className="mt-2 max-w-[46ch] text-sm text-ink-2">
            <span className="tabular">
              {summary.byThreat.shor} de {summary.total}
            </span>{' '}
            usos de criptografía los rompería una computadora cuántica con el algoritmo de Shor.
          </p>
        </div>

        <div aria-hidden="true" className="flex h-2 gap-px overflow-hidden rounded-full bg-paper">
          {THREATS.filter((threat) => summary.byThreat[threat] > 0).map((threat) => (
            <span
              key={threat}
              className={cn('h-full transition-[flex-grow] duration-700 ease-(--ease-swift)', SEVERITY_STYLES[THREAT_SEVERITY[threat]].bar)}
              style={{ flexGrow: summary.byThreat[threat] }}
            />
          ))}
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
          {THREATS.map((threat) => (
            <div key={threat} className="flex items-center gap-2.5">
              <span aria-hidden="true" className={cn('size-2.5 shrink-0 rounded-xs', SEVERITY_STYLES[THREAT_SEVERITY[threat]].bar)} />
              <dt className="min-w-0 flex-1 text-sm text-ink-2">{THREAT_LABEL[threat]}</dt>
              <dd className="text-sm font-semibold text-ink tabular">{summary.byThreat[threat]}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
