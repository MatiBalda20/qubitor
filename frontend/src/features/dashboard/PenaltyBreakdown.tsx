import { SeverityBadge } from '@/components/SeverityBadge'
import { cn } from '@/lib/cn'
import { formatNumber } from '@/lib/format'
import { SEVERITY_STYLES } from '@/lib/severityStyles'
import { SEVERITY_WEIGHT } from '@/lib/risk'
import { SEVERITIES, type Severity } from '@/types/Finding'

interface PenaltyBreakdownProps {
  /** Hallazgos que penalizan, contados por severidad. */
  counts: Record<Severity, number>
  className?: string
}

/** De dónde sale la penalización: cantidad × peso por severidad. */
export function PenaltyBreakdown({ counts, className }: PenaltyBreakdownProps) {
  const rows = SEVERITIES.map((severity) => ({
    severity,
    count: counts[severity],
    points: counts[severity] * SEVERITY_WEIGHT[severity],
  }))
  const total = rows.reduce((sum, row) => sum + row.points, 0)
  const largest = Math.max(...rows.map((row) => row.points), 1)

  return (
    <section aria-labelledby="penalty-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="penalty-title" className="text-base font-semibold text-ink">
          Penalización por severidad
        </h2>
        <p className="text-xs text-ink-3">Solo hallazgos abiertos y que no son falsos positivos</p>
      </header>

      <table className="w-full text-sm">
        <thead className="sr-only">
          <tr>
            <th scope="col">Severidad</th>
            <th scope="col">Hallazgos</th>
            <th scope="col">Peso</th>
            <th scope="col">Puntos</th>
            <th scope="col">Proporción</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {rows.map(({ severity, count, points }) => (
            <tr key={severity} className={cn(count === 0 && 'text-ink-3')}>
              <th scope="row" className="w-28 py-2.5 pl-5 text-left font-normal">
                <SeverityBadge severity={severity} className={cn(count === 0 && 'opacity-50')} />
              </th>
              <td className="w-12 py-2.5 text-right font-semibold tabular">{count}</td>
              <td className="w-16 py-2.5 pl-2 text-ink-3 tabular">× {formatNumber(SEVERITY_WEIGHT[severity])}</td>
              <td className="hidden py-2.5 pr-4 pl-2 sm:table-cell">
                <div className="h-2 rounded-full bg-paper">
                  <div
                    className={cn('h-full rounded-full transition-[width] duration-700 ease-(--ease-swift)', SEVERITY_STYLES[severity].bar)}
                    style={{ width: `${(points / largest) * 100}%` }}
                  />
                </div>
              </td>
              <td className="w-24 py-2.5 pr-5 text-right font-semibold tabular">
                {severity === 'info' ? <span className="font-normal text-ink-3">inventario</span> : `${formatNumber(points)} pts`}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-[3px] border-double border-rule-2">
            <th scope="row" colSpan={3} className="py-3 pl-5 text-left font-semibold text-ink">
              Total
            </th>
            <td className="hidden sm:table-cell" />
            <td className="py-3 pr-5 text-right font-display text-xl leading-none font-semibold text-ink tabular">
              {formatNumber(total)} pts
            </td>
          </tr>
        </tfoot>
      </table>
    </section>
  )
}
