import { SeverityBadge } from '@/components/SeverityBadge'
import { StatusStamp } from '@/components/StatusStamp'
import { cn } from '@/lib/cn'
import { pluralize } from '@/lib/format'
import { THREAT_LABEL, type CryptoUsage } from './quantum'

/** Inventario criptográfico (CBOM): todo uso de criptografía, también el seguro. */
export function CbomTable({
  usages,
  atRisk = new Set(),
}: {
  usages: readonly CryptoUsage[]
  /** Ids de los hallazgos que ya están en riesgo según la desigualdad de Mosca. */
  atRisk?: ReadonlySet<string>
}) {
  const algorithms = new Set(usages.map((u) => u.algorithm)).size

  return (
    <section aria-labelledby="cbom-title" className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="cbom-title" className="text-base font-semibold text-ink">
          Inventario criptográfico (CBOM)
        </h2>
        <p className="text-xs text-ink-3 tabular">
          {pluralize(usages.length, 'uso', 'usos')} · {pluralize(algorithms, 'algoritmo', 'algoritmos')}
        </p>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] text-sm">
          <thead>
            <tr className="border-b border-rule bg-paper/60">
              <th scope="col" className="field-label py-2 pl-5 text-left">
                Algoritmo
              </th>
              <th scope="col" className="field-label px-3 py-2 text-left">
                Amenaza cuántica
              </th>
              <th scope="col" className="field-label px-3 py-2 text-left">
                Ubicación
              </th>
              <th scope="col" className="field-label py-2 pr-5 text-right">
                Severidad
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {usages.map((usage) => (
              <tr key={usage.finding.id}>
                <th scope="row" className="py-2.5 pl-5 text-left font-medium">
                  <span className={cn('text-ink', !usage.active && 'text-ink-3 line-through decoration-ink-3/60')}>
                    {usage.algorithm}
                  </span>
                  {!usage.active && <StatusStamp status={usage.finding.status} className="ml-2 align-middle" />}
                </th>
                <td className="px-3 py-2.5 text-ink-2">
                  {THREAT_LABEL[usage.threat]}
                  {atRisk.has(usage.finding.id) && (
                    <span className="ml-2 rounded-xs bg-sev-high-soft px-1.5 py-0.5 text-xs font-semibold text-sev-high-ink ring-1 ring-sev-high/45 ring-inset">
                      En riesgo hoy
                    </span>
                  )}
                </td>
                <td className="px-3 py-2.5 font-mono text-[0.8125rem] text-ink-2">{usage.location}</td>
                <td className="py-2 pr-5 text-right">
                  <SeverityBadge severity={usage.finding.severity} size="sm" className={cn(!usage.active && 'opacity-55')} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
