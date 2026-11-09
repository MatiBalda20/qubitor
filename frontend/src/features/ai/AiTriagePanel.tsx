import { ArrowRight, Sparkles } from 'lucide-react'
import { SeverityBadge } from '@/components/SeverityBadge'
import { cn } from '@/lib/cn'
import type { FindingRecord } from '@/types/Finding'
import { remediationSteps } from './remediation'

interface AiTriagePanelProps {
  finding: FindingRecord
  /** Muestra el cambio de severidad motor → IA. FindingCard ya lo muestra en sus datos. */
  showSeverityChange?: boolean
  className?: string
}

/**
 * Evaluación de la IA de un hallazgo (Módulo E): si parece falso positivo, la
 * severidad ajustada, por qué importa y los pasos para remediarlo. Lo usa
 * FindingCard, así que aparece en el dashboard y en las vistas de los Módulos C y D.
 * Sin triage no muestra nada.
 */
export function AiTriagePanel({ finding, showSeverityChange = true, className }: AiTriagePanelProps) {
  const triage = finding.triage
  if (!triage) return null

  const adjusted = showSeverityChange && triage.adjusted_severity !== finding.severity
  const steps = remediationSteps(triage.remediation)

  return (
    <section aria-label="Evaluación de la IA" className={cn('space-y-3 rounded-sm bg-civic-soft/60 p-4 ring-1 ring-civic/10', className)}>
      <div className="flex flex-wrap items-center gap-2">
        <Sparkles className="size-4 text-civic" strokeWidth={1.75} aria-hidden="true" />
        <h4 className="text-sm font-semibold text-ink">Evaluación de la IA</h4>
        {triage.is_false_positive && (
          <span className="rounded-xs bg-stamp/10 px-1.5 py-0.5 text-xs font-semibold text-stamp">Posible falso positivo</span>
        )}
      </div>

      {adjusted && (
        <p className="flex flex-wrap items-center gap-2 text-xs text-ink-2">
          <span>Severidad del motor</span>
          <SeverityBadge severity={finding.severity} size="sm" />
          <ArrowRight className="size-3.5 text-ink-3" strokeWidth={1.75} aria-hidden="true" />
          <span>según la IA</span>
          <SeverityBadge severity={triage.adjusted_severity} size="sm" />
        </p>
      )}

      {triage.explanation && <p className="max-w-[75ch] text-sm text-ink-2">{triage.explanation}</p>}

      {steps.length > 0 && (
        <div>
          <p className="field-label mb-1">Remediación sugerida</p>
          {steps.length === 1 ? (
            <p className="max-w-[75ch] text-sm text-ink">{steps[0]}</p>
          ) : (
            <ol className="max-w-[75ch] list-decimal space-y-1 pl-5 text-sm text-ink marker:text-ink-3">
              {steps.map((step, index) => (
                <li key={index}>{step}</li>
              ))}
            </ol>
          )}
        </div>
      )}

      {triage.is_false_positive && (
        <p className="text-xs text-ink-2">
          No cuenta para el Risk Score mientras la IA lo considere falso positivo. Si lo confirmás, marcalo como falso positivo.
        </p>
      )}
      <p className="text-xs text-ink-3">Generado por IA a partir de un fragmento del código: revisalo antes de aplicarlo.</p>
    </section>
  )
}
