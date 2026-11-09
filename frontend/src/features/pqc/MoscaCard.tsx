import { useId } from 'react'
import { cn } from '@/lib/cn'
import { pluralize } from '@/lib/format'
import { clampYears, MAX_YEARS, NIST_DISALLOW_YEAR, type MoscaGroup, type MoscaParams, type MoscaVerdict } from './mosca'

const GROUP_LABEL: Record<MoscaGroup, string> = {
  data: 'Datos cifrados e intercambio de claves',
  signature: 'Firmas',
}

/** Urgencia de migración según la desigualdad de Mosca (X + Y > Z). */
export function MoscaCard({
  params,
  verdicts,
  onChange,
  className,
}: {
  params: MoscaParams
  verdicts: readonly MoscaVerdict[]
  onChange: (params: MoscaParams) => void
  className?: string
}) {
  const set = (key: keyof MoscaParams) => (value: number) => onChange({ ...params, [key]: clampYears(value) })

  return (
    <section aria-labelledby="mosca-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="mosca-title" className="text-base font-semibold text-ink">
          Urgencia de migración
        </h2>
        <p className="text-xs text-ink-3">Desigualdad de Mosca</p>
      </header>

      <div className="space-y-5 px-5 py-5">
        <p className="max-w-[60ch] text-sm text-ink-2">
          Si los años que algo tiene que seguir protegido (<strong className="font-semibold text-ink">X</strong>) más los
          que lleva migrar (<strong className="font-semibold text-ink">Y</strong>) superan los que faltan para una
          computadora cuántica (<strong className="font-semibold text-ink">Z</strong>), ya está en riesgo hoy.
        </p>

        <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
          <YearsField label="X · Datos secretos por" value={params.dataYears} onChange={set('dataYears')} />
          <YearsField label="X · Firmas válidas por" value={params.signatureYears} onChange={set('signatureYears')} />
          <YearsField label="Y · Migración" value={params.migrationYears} onChange={set('migrationYears')} />
          <YearsField
            label="Z · Computadora cuántica en"
            value={params.quantumYears}
            onChange={set('quantumYears')}
            hint={`Por defecto, hasta ${NIST_DISALLOW_YEAR}: NIST deja de permitir RSA y curvas elípticas (NIST IR 8547).`}
          />
        </div>

        {verdicts.length === 0 ? (
          <p className="text-sm text-ink-2">No hay criptografía vulnerable a Shor: no queda nada que evaluar.</p>
        ) : (
          <ul aria-live="polite" className="divide-y divide-rule border-t border-rule">
            {verdicts.map((verdict) => (
              <li key={verdict.group} className="space-y-1.5 pt-3.5 [&:not(:last-child)]:pb-3.5">
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
                  <h3 className="text-sm font-semibold text-ink">{GROUP_LABEL[verdict.group]}</h3>
                  <span
                    className={cn(
                      'rounded-xs px-1.5 py-0.5 text-xs font-semibold ring-1 ring-inset',
                      verdict.atRisk
                        ? 'bg-sev-high-soft text-sev-high-ink ring-sev-high/45'
                        : 'bg-ok-soft text-ok ring-ok/40',
                    )}
                  >
                    {verdict.atRisk
                      ? `En riesgo · faltan ${pluralize(-verdict.margin, 'año', 'años')}`
                      : `Con margen · ${pluralize(verdict.margin, 'año', 'años')}`}
                  </span>
                </div>
                <p className="text-sm text-ink-2 tabular">
                  {verdict.shelfLife} + {params.migrationYears} = {verdict.total} {verdict.atRisk ? '>' : '≤'}{' '}
                  {params.quantumYears} años · {pluralize(verdict.usages.length, 'uso', 'usos')}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

function YearsField({
  label,
  value,
  onChange,
  hint,
}: {
  label: string
  value: number
  onChange: (value: number) => void
  hint?: string
}) {
  const id = useId()
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="field-label block">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={0}
          max={MAX_YEARS}
          step={1}
          value={value}
          onChange={(event) => onChange(event.target.valueAsNumber)}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className="h-9 w-20 rounded-sm bg-sheet px-2.5 text-sm text-ink tabular ring-1 ring-rule-2 ring-inset hover:ring-ink-3"
        />
        <span className="text-sm text-ink-2">años</span>
      </div>
      {hint && (
        <p id={`${id}-hint`} className="max-w-[40ch] text-xs text-ink-3">
          {hint}
        </p>
      )}
    </div>
  )
}
