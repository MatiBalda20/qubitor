import { ArrowDown, ArrowUp, FolderGit2, Radar, RefreshCw, ServerCrash, TriangleAlert } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/layout/PageHeader'
import { Skeleton } from '@/components/Loader'
import { cn } from '@/lib/cn'
import { USE_MOCKS } from '@/lib/config'
import { formatDateTime, formatDuration, formatNumber, pluralize } from '@/lib/format'
import { ENGINE_LABEL } from '@/lib/labels'
import type { EngineName } from '@/types/Finding'
import { loadHistory, type HistoryData, type HistoryScan } from './dataSource'
import { GRADE_TEXT, historyRows, SCAN_STATUS_LABEL, scoreTrend, type HistoryRow } from './scans'

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'empty' }
  | { status: 'ready'; data: HistoryData }

/** Vista «Historial» (Módulo A): escaneos del repositorio y cómo cambió su Risk Score. */
export default function HistoryPage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  const load = useCallback(async () => {
    try {
      const data = await loadHistory()
      setState(data ? { status: 'ready', data } : { status: 'empty' })
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : 'Error desconocido.' })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (state.status === 'loading') return <HistorySkeleton />

  if (state.status === 'error') {
    return (
      <>
        <PageHeader title="Historial" />
        <EmptyState
          icon={ServerCrash}
          tone="error"
          title="No pudimos cargar el historial"
          description={state.message}
          action={
            <button
              type="button"
              onClick={() => {
                setState({ status: 'loading' })
                load()
              }}
              className="inline-flex h-10 items-center gap-2 rounded-sm bg-civic px-4 text-sm font-semibold text-civic-ink hover:bg-civic-deep active:scale-[0.96]"
            >
              <RefreshCw className="size-4" strokeWidth={2} aria-hidden="true" />
              Reintentar
            </button>
          }
        />
      </>
    )
  }

  if (state.status === 'empty') {
    return (
      <>
        <PageHeader title="Historial" />
        <EmptyState
          icon={FolderGit2}
          title="Todavía no conectaste un repositorio"
          description="Conectá un repositorio y escanealo para empezar su historial."
          action={
            <Link
              to="/connect"
              className="inline-flex h-10 items-center rounded-sm bg-civic px-4 text-sm font-semibold text-civic-ink hover:bg-civic-deep"
            >
              Conectar repositorio
            </Link>
          }
        />
      </>
    )
  }

  return <HistoryView data={state.data} />
}

function HistoryView({ data }: { data: HistoryData }) {
  const { repository, scans } = data
  const rows = useMemo(() => historyRows(scans), [scans])
  const trend = useMemo(() => scoreTrend(scans), [scans])

  return (
    <>
      <PageHeader
        title="Historial"
        meta={
          <span className="flex flex-wrap gap-x-2 gap-y-1">
            <span>{repository.full_name}</span>
            <span className="tabular">
              <span aria-hidden="true" className="mr-2">·</span>
              {pluralize(scans.length, 'escaneo', 'escaneos')}
            </span>
          </span>
        }
      />

      <div className="space-y-5 px-4 pb-12 sm:px-8">
        {USE_MOCKS && (
          <p className="text-xs text-ink-3">
            Datos de ejemplo de <code className="font-mono">features/history/mock.json</code>: la API todavía no está conectada.
          </p>
        )}

        {scans.length === 0 ? (
          <div className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
            <EmptyState
              icon={Radar}
              title="Este repositorio todavía no tiene escaneos"
              description="Lanzá un escaneo desde el dashboard: cada uno queda registrado acá."
              action={
                <Link to="/" className="text-sm font-semibold text-civic underline decoration-civic/30 hover:decoration-civic">
                  Ir al dashboard
                </Link>
              }
            />
          </div>
        ) : (
          <>
            {trend && (
              <p className="max-w-[75ch] text-sm text-ink-2">
                El Risk Score pasó de <strong className="font-semibold text-ink tabular">{formatNumber(trend.first)}</strong> en
                el primer escaneo a <strong className="font-semibold text-ink tabular">{formatNumber(trend.latest)}</strong> en
                el último. Cada escaneo completado se compara con el anterior.
              </p>
            )}
            <ScanTable rows={rows} />
          </>
        )}
      </div>
    </>
  )
}

// La tabla en columnas necesita el ancho de xl (el menú lateral ocupa lugar desde lg); antes, cada escaneo es una ficha.
const COLUMNS = 'xl:grid-cols-[minmax(10rem,1.3fr)_minmax(7rem,1fr)_3rem_5rem_5.5rem_6rem_minmax(4.5rem,1fr)]'

function ScanTable({ rows }: { rows: readonly HistoryRow[] }) {
  return (
    <section aria-labelledby="scans-title" className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="scans-title" className="text-base font-semibold text-ink">
          Escaneos
        </h2>
        <p className="text-xs text-ink-3">Del más reciente al más antiguo</p>
      </header>

      <div aria-hidden="true" className={cn('hidden gap-4 border-b border-rule bg-paper/60 px-5 py-2 xl:grid', COLUMNS)}>
        {['Fecha', 'Estado', 'Nota', 'Risk Score', 'Cambio', 'Duración', 'Commit'].map((label) => (
          <span key={label} className="field-label">
            {label}
          </span>
        ))}
      </div>

      <ul className="divide-y divide-rule">
        {rows.map((row) => (
          <ScanRow key={row.scan.id} row={row} />
        ))}
      </ul>
    </section>
  )
}

function ScanRow({ row }: { row: HistoryRow }) {
  const { scan, delta } = row
  const failedEngines = Object.keys(scan.engine_errors ?? {}) as EngineName[]

  return (
    <li className="px-4 py-3.5 sm:px-5">
      <dl className={cn('grid grid-cols-2 items-baseline gap-x-4 gap-y-2.5 text-sm sm:grid-cols-4 xl:gap-y-0', COLUMNS)}>
        <Cell label="Fecha" className="col-span-2 sm:col-span-2 xl:col-span-1">
          <span className="text-ink tabular">{formatDateTime(scan.finished_at ?? scan.started_at)}</span>
        </Cell>
        <Cell label="Estado">
          <ScanStatusText scan={scan} />
        </Cell>
        <Cell label="Nota">
          {scan.grade ? (
            <span className={cn('font-display text-xl leading-none font-semibold', GRADE_TEXT[scan.grade])} aria-label={`Nota ${scan.grade}`}>
              {scan.grade}
            </span>
          ) : (
            <Empty />
          )}
        </Cell>
        <Cell label="Risk Score">
          {scan.risk_score === null ? <Empty /> : <span className="font-semibold text-ink tabular">{formatNumber(scan.risk_score)}</span>}
        </Cell>
        <Cell label="Cambio">
          <ScoreDelta delta={delta} />
        </Cell>
        <Cell label="Duración">
          {scan.finished_at ? (
            <span className="text-ink-2 tabular">{formatDuration(scan.started_at, scan.finished_at)}</span>
          ) : (
            <Empty />
          )}
        </Cell>
        <Cell label="Commit" className="min-w-0">
          {scan.commit_sha ? (
            <span className="font-mono text-[0.8125rem] text-ink-2" title={scan.commit_sha}>
              {scan.commit_sha.slice(0, 7)}
            </span>
          ) : (
            <Empty />
          )}
        </Cell>
      </dl>

      {scan.status === 'failed' && scan.error && <p className="mt-2 max-w-[75ch] text-xs text-ink-2">{scan.error}</p>}
      {scan.status === 'completed' && failedEngines.length > 0 && (
        <p className="mt-2 flex max-w-[75ch] items-start gap-1.5 text-xs text-ink-2">
          <TriangleAlert className="mt-px size-3.5 shrink-0 text-ink-3" strokeWidth={1.75} aria-hidden="true" />
          Escaneo parcial: no corrió {failedEngines.map((e) => ENGINE_LABEL[e] ?? e).join(', ')}. La nota no incluye sus hallazgos.
        </p>
      )}
    </li>
  )
}

/** Celda con su rótulo: visible en la ficha, en la cabecera de columnas desde xl. */
function Cell({ label, className, children }: { label: string; className?: string; children: ReactNode }) {
  return (
    <div className={className}>
      <dt className="field-label mb-0.5 xl:sr-only">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function ScanStatusText({ scan }: { scan: HistoryScan }) {
  const active = scan.status === 'queued' || scan.status === 'running'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium',
        scan.status === 'failed' ? 'text-sev-critical' : active ? 'text-civic' : 'text-ink-2',
      )}
    >
      {active && <span aria-hidden="true" className="size-1.5 animate-pulse rounded-full bg-civic motion-reduce:animate-none" />}
      {SCAN_STATUS_LABEL[scan.status]}
    </span>
  )
}

function ScoreDelta({ delta }: { delta: number | null }) {
  if (delta === null) return <Empty />
  if (delta === 0) return <span className="text-ink-3">Sin cambios</span>
  const Icon = delta > 0 ? ArrowUp : ArrowDown
  return (
    <span className="inline-flex items-center gap-1 text-ink-2 tabular">
      <Icon className="size-3.5" strokeWidth={2} aria-hidden="true" />
      <span className="sr-only">{delta > 0 ? 'Subió' : 'Bajó'}</span>
      {delta > 0 ? '+' : '−'}
      {formatNumber(Math.abs(delta))}
    </span>
  )
}

function Empty() {
  return (
    <span className="text-ink-3" aria-label="Sin dato">
      —
    </span>
  )
}

function HistorySkeleton() {
  return (
    <div role="status" aria-label="Cargando el historial">
      <div className="space-y-2.5 px-4 pt-9 pb-6 sm:px-8">
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      <div className="space-y-5 px-4 sm:px-8">
        <Skeleton className="h-4 w-96 max-w-full" />
        <Skeleton className="h-80" />
      </div>
    </div>
  )
}
