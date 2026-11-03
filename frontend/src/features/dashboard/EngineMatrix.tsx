import { ENGINE_LABEL, SEVERITY_LABEL } from '@/lib/labels'
import { cn } from '@/lib/cn'
import { SEVERITY_STYLES } from '@/lib/severityStyles'
import { ENGINES, SEVERITIES, type EngineName, type Severity } from '@/types/Finding'

interface EngineMatrixProps {
  /** Hallazgos abiertos por motor y severidad. */
  counts: Record<EngineName, Record<Severity, number>>
  className?: string
}

/** Hallazgos abiertos cruzados por motor y severidad. Al apuntar una fila, el resto se atenúa. */
export function EngineMatrix({ counts, className }: EngineMatrixProps) {
  return (
    <section aria-labelledby="engine-matrix-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="border-b border-rule px-5 py-3.5">
        <h2 id="engine-matrix-title" className="text-base font-semibold text-ink">
          Abiertos por motor
        </h2>
      </header>
      <div className="overflow-x-auto">
        <table className="group/matrix w-full min-w-[30rem] text-sm">
          <thead>
            <tr className="border-b border-rule">
              <th scope="col" className="field-label py-2 pl-5 text-left">
                Motor
              </th>
              {SEVERITIES.map((severity) => (
                <th key={severity} scope="col" className="field-label px-1 py-2 text-center">
                  {SEVERITY_LABEL[severity]}
                </th>
              ))}
              <th scope="col" className="field-label py-2 pr-5 text-right">
                Total
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {ENGINES.map((engine) => {
              const row = counts[engine]
              const total = SEVERITIES.reduce((sum, s) => sum + row[s], 0)
              return (
                <tr
                  key={engine}
                  className="transition-opacity duration-200 group-hover/matrix:opacity-45 hover:!opacity-100 focus-within:!opacity-100"
                >
                  <th scope="row" className="py-2.5 pl-5 text-left font-medium text-ink">
                    {ENGINE_LABEL[engine]}
                  </th>
                  {SEVERITIES.map((severity) => (
                    <td key={severity} className="px-1 py-1.5 text-center">
                      <Cell count={row[severity]} severity={severity} />
                    </td>
                  ))}
                  <td className="py-2.5 pr-5 text-right font-semibold text-ink tabular">{total}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Cell({ count, severity }: { count: number; severity: Severity }) {
  if (count === 0) {
    return (
      <span className="text-ink-3/60" aria-label="ninguno">
        ·
      </span>
    )
  }
  return (
    <span
      className={cn(
        'inline-grid h-7 min-w-9 place-items-center rounded-xs px-1.5 font-semibold tabular ring-1 ring-inset',
        SEVERITY_STYLES[severity].badge,
      )}
    >
      {count}
    </span>
  )
}
