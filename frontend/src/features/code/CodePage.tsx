import { FolderGit2, Radar, RefreshCw, ServerCrash, ShieldCheck } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/layout/PageHeader'
import { Skeleton } from '@/components/Loader'
import { FindingsTable } from '@/components/FindingsTable'
import { useToast } from '@/components/toast/toastContext'
import { USE_MOCKS } from '@/lib/config'
import { formatDateTime } from '@/lib/format'
import { dashboardSource, type DashboardData } from '@/features/dashboard/dataSource'
import type { FindingRecord, FindingStatus } from '@/types/Finding'

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'empty' }
  | { status: 'ready'; data: DashboardData }

const TITLE = 'Código inseguro'

export default function CodePage() {
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const toast = useToast()

  const load = useCallback(async () => {
    try {
      const data = await dashboardSource.load()
      setState(data ? { status: 'ready', data } : { status: 'empty' })
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : 'Error desconocido.' })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleStatusChange = async (finding: FindingRecord, newStatus: FindingStatus) => {
    if (state.status !== 'ready') return
    try {
      setState({
        ...state,
        data: {
          ...state.data,
          findings: state.data.findings.map((f) => (f.id === finding.id ? { ...f, status: newStatus } : f)),
        },
      })
      await dashboardSource.updateFinding(finding.id, newStatus)
      toast({
        message: `Estado actualizado a ${newStatus === 'resolved' ? 'Resuelto' : newStatus === 'false_positive' ? 'Falso positivo' : 'Abierto'}`,
      })
    } catch {
      toast({ message: 'Error al actualizar el estado', tone: 'error' })
      load()
    }
  }

  if (state.status === 'loading') {
    return (
      <div role="status" aria-label="Cargando hallazgos de código">
        <div className="space-y-2.5 px-4 pt-9 pb-6 sm:px-8">
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-4 w-80 max-w-full" />
        </div>
        <div className="px-4 sm:px-8">
          <Skeleton className="h-96" />
        </div>
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <>
        <PageHeader title={TITLE} />
        <EmptyState
          icon={ServerCrash}
          tone="error"
          title="No pudimos cargar los hallazgos de código"
          description={state.message}
          action={
            <button
              onClick={() => {
                setState({ status: 'loading' })
                load()
              }}
              className="inline-flex h-10 items-center gap-2 rounded-sm bg-civic px-4 text-sm font-semibold text-civic-ink hover:bg-civic-deep"
            >
              <RefreshCw className="size-4" aria-hidden="true" /> Reintentar
            </button>
          }
        />
      </>
    )
  }

  if (state.status === 'empty') {
    return (
      <>
        <PageHeader title={TITLE} />
        <EmptyState
          icon={FolderGit2}
          title="Todavía no conectaste un repositorio"
          description="Conectá un repositorio y escanealo para detectar inyecciones SQL, uso de eval() y mala criptografía."
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

  const { repository, scan, findings } = state.data
  const codeFindings = findings.filter(
    (f) => f.engine === 'sast' || (f.engine === 'crypto' && !f.rule_id.startsWith('crypto.pqc.')),
  )

  return (
    <>
      <PageHeader
        title={TITLE}
        meta={
          <span className="flex flex-wrap gap-x-2 gap-y-1">
            <span>{repository.full_name}</span>
            {scan?.finished_at && (
              <span className="tabular">
                <span aria-hidden="true" className="mr-2">·</span>último escaneo {formatDateTime(scan.finished_at)}
              </span>
            )}
          </span>
        }
      />

      <div className="space-y-5 px-4 pb-12 sm:px-8">
        {USE_MOCKS && (
          <p className="text-xs text-ink-3">Datos de ejemplo: la API todavía no está conectada.</p>
        )}

        {scan === null ? (
          <div className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
            <EmptyState
              icon={Radar}
              title="Este repositorio todavía no tiene escaneos"
              description="Lanzá un escaneo desde el dashboard."
              action={
                <Link to="/" className="text-sm font-semibold text-civic underline decoration-civic/30 hover:decoration-civic">
                  Ir al dashboard
                </Link>
              }
            />
          </div>
        ) : codeFindings.length === 0 ? (
          <div className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
            <EmptyState
              icon={ShieldCheck}
              title="No hay código inseguro"
              description="El escaneo no detectó vulnerabilidades de código fuente (SAST) ni de criptografía clásica."
            />
          </div>
        ) : (
          <FindingsTable
            findings={codeFindings}
            title="Hallazgos de código"
            engines={['sast', 'crypto']}
            onStatusChange={handleStatusChange}
          />
        )}
      </div>
    </>
  )
}