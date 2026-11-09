import { Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Skeleton } from '@/components/Loader'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'
import { loadExecutiveSummary } from './summaryData'
import type { ExecutiveSummary, RiskPriority, TriageStatus } from './types'

type LoadState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: ExecutiveSummary }

const PRIORITY_LABEL: Record<RiskPriority, string> = {
  inmediata: 'Prioridad inmediata',
  alta: 'Prioridad alta',
  media: 'Prioridad media',
}

/** Aviso cuando la IA no evaluó todos los hallazgos: el resumen y el score usan la severidad del motor. */
const TRIAGE_NOTICE: Partial<Record<TriageStatus, string>> = {
  partial: 'La IA evaluó solo una parte de los hallazgos.',
  quota_exceeded: 'Se agotó la cuota de Gemini: algunos hallazgos quedaron sin evaluar.',
  unavailable: 'Gemini no respondió: los hallazgos quedaron con la severidad del motor.',
  disabled: 'La evaluación con IA no está configurada en este entorno.',
}

/**
 * Resumen ejecutivo del último escaneo (Módulo E), arriba del dashboard general:
 * estado en lenguaje de negocio, los tres riesgos principales y qué hacer primero.
 * Si no se puede cargar, no bloquea el resto del dashboard.
 */
export function ExecutiveSummaryCard({ scanId, className }: { scanId: string; className?: string }) {
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    loadExecutiveSummary(scanId)
      .then((data) => !cancelled && setState({ status: 'ready', data }))
      .catch((error: unknown) => {
        if (!cancelled) setState({ status: 'error', message: error instanceof Error ? error.message : 'Error desconocido.' })
      })
    return () => {
      cancelled = true
    }
  }, [scanId])

  return (
    <section aria-labelledby="executive-summary-title" className={cn('rounded-sm bg-sheet shadow-sheet ring-1 ring-rule', className)}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="executive-summary-title" className="text-base font-semibold text-ink">
          Resumen ejecutivo
        </h2>
        {state.status === 'ready' && state.data.available && <GeneratedBy data={state.data} />}
      </header>

      <div className="px-5 py-4">
        {state.status === 'loading' && (
          <div role="status" aria-label="Cargando el resumen ejecutivo" className="space-y-2.5">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        )}

        {state.status === 'error' && (
          <p className="text-sm text-ink-2">No pudimos cargar el resumen ejecutivo: {state.message}</p>
        )}

        {state.status === 'ready' && !state.data.available && (
          <p className="text-sm text-ink-2">El resumen ejecutivo se genera al terminar el próximo escaneo.</p>
        )}

        {state.status === 'ready' && state.data.available && <SummaryBody data={state.data} />}
      </div>
    </section>
  )
}

function GeneratedBy({ data }: { data: ExecutiveSummary }) {
  const byAi = data.generated_by === 'gemini'
  return (
    <p className="inline-flex items-center gap-1.5 text-xs text-ink-3">
      {byAi && <Sparkles className="size-3.5 text-civic" strokeWidth={1.75} aria-hidden="true" />}
      {byAi ? 'Generado con IA' : 'Resumen automático, sin IA'}
      {data.generated_at && <span className="tabular">· {formatDateTime(data.generated_at)}</span>}
    </p>
  )
}

function SummaryBody({ data }: { data: ExecutiveSummary }) {
  const notice = data.triage_status ? TRIAGE_NOTICE[data.triage_status] : undefined
  return (
    <div className="space-y-4">
      {data.headline && <p className="text-base font-semibold text-ink">{data.headline}</p>}
      {data.summary && <p className="max-w-[75ch] text-sm text-ink-2">{data.summary}</p>}

      {data.top_risks.length > 0 && (
        <div>
          <p className="field-label mb-2">Riesgos principales</p>
          <ol className="divide-y divide-rule rounded-sm ring-1 ring-rule">
            {data.top_risks.map((risk, index) => (
              <li key={`${risk.title}-${index}`} className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-x-2 px-3 py-2.5">
                <span className="text-sm font-semibold text-ink-3 tabular">{index + 1}.</span>
                <div className="min-w-0 space-y-0.5">
                  <p className="flex flex-wrap items-baseline gap-x-2 text-sm font-semibold text-ink">
                    {risk.title}
                    <span className={cn('text-xs font-semibold', risk.priority === 'inmediata' ? 'text-stamp' : 'text-ink-3')}>
                      {PRIORITY_LABEL[risk.priority]}
                    </span>
                  </p>
                  <p className="text-sm text-ink-2">{risk.impact}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {data.priorities.length > 0 && (
        <div>
          <p className="field-label mb-1">Qué hacer primero</p>
          <ol className="max-w-[75ch] list-decimal space-y-1 pl-5 text-sm text-ink marker:text-ink-3">
            {data.priorities.map((priority, index) => (
              <li key={`${priority}-${index}`}>{priority}</li>
            ))}
          </ol>
        </div>
      )}

      {notice && <p className="text-xs text-ink-3">{notice}</p>}
    </div>
  )
}
