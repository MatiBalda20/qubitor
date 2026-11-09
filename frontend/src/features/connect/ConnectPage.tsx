import { Archive, ArrowRight, FolderGit2, GitBranch, Link2, Lock, RefreshCw, Search, ServerCrash } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/layout/PageHeader'
import { Skeleton } from '@/components/Loader'
import { ScanProgress } from '@/components/ScanProgress'
import { useToast } from '@/components/toast/toastContext'
import { useScanPolling } from '@/hooks/useScanPolling'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { USE_MOCKS } from '@/lib/config'
import { formatDateTime, pluralize } from '@/lib/format'
import type { Repository } from '@/types/Scan'
import { connectSource } from './dataSource'
import { filterRepos, formatSize, isGitHubUrl, sortForConnect } from './search'
import type { GitHubRepo } from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string; notLinked: boolean }
  | { status: 'ready' }

const PRIMARY_BUTTON =
  'inline-flex h-10 items-center justify-center gap-2 rounded-sm bg-civic px-4 text-sm font-semibold text-civic-ink hover:bg-civic-deep active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-60'
const SECONDARY_BUTTON =
  'inline-flex h-9 items-center justify-center gap-2 rounded-sm bg-sheet px-3 text-sm font-semibold text-ink ring-1 ring-rule-2 ring-inset hover:bg-civic-soft disabled:cursor-not-allowed disabled:opacity-60'
const INPUT =
  'h-9 w-full rounded-sm bg-sheet pr-3 pl-9 text-sm text-ink ring-1 ring-rule-2 ring-inset placeholder:text-ink-3 hover:ring-ink-3'

/** Vista «Conectar repositorio» (Módulo E): repos de GitHub del usuario, búsqueda y primer escaneo. */
export default function ConnectPage() {
  const toast = useToast()
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [started, setStarted] = useState<{ repository: Repository; scanId: string } | null>(null)

  const { scan, error: pollError } = useScanPolling(started?.scanId ?? null, { fetchScan: connectSource.getScan })

  const loadFirstPage = useCallback(async () => {
    setState({ status: 'loading' })
    try {
      const first = await connectSource.listGitHubRepos(1)
      setRepos(first.items)
      setPage(1)
      setHasNext(first.has_next)
      setState({ status: 'ready' })
    } catch (error) {
      setState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Error desconocido.',
        notLinked: error instanceof ApiError && error.status === 409,
      })
    }
  }, [])

  useEffect(() => {
    loadFirstPage()
  }, [loadFirstPage])

  async function loadMore() {
    setLoadingMore(true)
    try {
      const next = await connectSource.listGitHubRepos(page + 1)
      setRepos((current) => [...current, ...next.items.filter((r) => !current.some((c) => c.full_name === r.full_name))])
      setPage(next.page)
      setHasNext(next.has_next)
    } catch (error) {
      toast({ message: error instanceof Error ? error.message : 'No se pudieron cargar más repositorios.', tone: 'error' })
    } finally {
      setLoadingMore(false)
    }
  }

  /** Conecta el repo y lanza su escaneo. `connect` devuelve el repo creado (o el existente). */
  async function connectAndScan(key: string, connect: () => Promise<Repository>) {
    setBusy(key)
    try {
      const repository = await connect()
      const firstScan = await connectSource.startScan(repository.id)
      setStarted({ repository, scanId: firstScan.id })
      setRepos((current) => current.map((r) => (r.url.toLowerCase() === repository.url.toLowerCase() ? { ...r, connected: true } : r)))
      toast({ message: `Conectamos ${repository.full_name} y empezó su escaneo.` })
    } catch (error) {
      toast({ message: error instanceof Error ? error.message : 'No se pudo conectar el repositorio.', tone: 'error' })
    } finally {
      setBusy(null)
    }
  }

  const visible = useMemo(() => sortForConnect(filterRepos(repos, query)), [repos, query])

  return (
    <>
      <PageHeader
        title="Conectar repositorio"
        meta="Elegí un repositorio de tu cuenta de GitHub o pegá la URL de uno público. Qubitor lo clona, lo analiza y borra el código al terminar."
      />

      <div className="space-y-5 px-4 pb-12 sm:px-8">
        {USE_MOCKS && (
          <p className="text-xs text-ink-3">
            Datos de ejemplo de <code className="font-mono">features/connect/mock.json</code>: la API todavía no está conectada.
          </p>
        )}

        {started && (
          <section aria-live="polite" className="space-y-3">
            <ScanProgress scan={scan} error={pollError} />
            {scan?.status === 'completed' && (
              <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-semibold text-civic underline decoration-civic/30 hover:decoration-civic">
                Ver los resultados de {started.repository.full_name} en el dashboard
                <ArrowRight className="size-4" strokeWidth={2} aria-hidden="true" />
              </Link>
            )}
          </section>
        )}

        <section aria-labelledby="github-repos-title" className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-5 py-3.5">
            <h2 id="github-repos-title" className="text-base font-semibold text-ink">
              Tus repositorios de GitHub
            </h2>
            <label className="relative w-full sm:w-72">
              <span className="sr-only">Buscar repositorio</span>
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-3" strokeWidth={1.75} aria-hidden="true" />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar por nombre o descripción"
                className={INPUT}
                disabled={state.status !== 'ready'}
              />
            </label>
          </header>

          {state.status === 'loading' && <RepoListSkeleton />}

          {state.status === 'error' && (
            <EmptyState
              icon={state.notLinked ? FolderGit2 : ServerCrash}
              tone={state.notLinked ? 'neutral' : 'error'}
              title={state.notLinked ? 'Tu cuenta de GitHub no está vinculada' : 'No pudimos traer tus repositorios'}
              description={
                state.notLinked
                  ? `${state.message}. Cerrá sesión y volvé a entrar con GitHub, o pegá la URL de un repositorio público más abajo.`
                  : state.message
              }
              action={
                <button type="button" onClick={loadFirstPage} className={PRIMARY_BUTTON}>
                  <RefreshCw className="size-4" strokeWidth={2} aria-hidden="true" />
                  Reintentar
                </button>
              }
            />
          )}

          {state.status === 'ready' && repos.length === 0 && (
            <EmptyState
              icon={FolderGit2}
              title="Tu cuenta no tiene repositorios"
              description="Creá uno en GitHub o pegá la URL de un repositorio público más abajo."
            />
          )}

          {state.status === 'ready' && repos.length > 0 && (
            <>
              {visible.length === 0 ? (
                <EmptyState
                  icon={Search}
                  title="Ningún repositorio coincide con la búsqueda"
                  description={hasNext ? 'Puede estar en las páginas que todavía no se cargaron.' : undefined}
                  action={
                    <button type="button" onClick={() => setQuery('')} className="text-sm font-semibold text-civic underline decoration-civic/30 hover:decoration-civic">
                      Limpiar la búsqueda
                    </button>
                  }
                />
              ) : (
                <ul className="divide-y divide-rule">
                  {visible.map((repo) => (
                    <RepoRow
                      key={repo.full_name}
                      repo={repo}
                      busy={busy === repo.full_name}
                      disabled={busy !== null}
                      onConnect={() => connectAndScan(repo.full_name, () => connectSource.connectGitHubRepo(repo.full_name))}
                    />
                  ))}
                </ul>
              )}
              <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-rule px-5 py-3">
                <p className="text-xs text-ink-3 tabular">
                  {pluralize(repos.length, 'repositorio cargado', 'repositorios cargados')}
                </p>
                {hasNext && (
                  <button type="button" onClick={loadMore} disabled={loadingMore} className={SECONDARY_BUTTON}>
                    {loadingMore ? 'Cargando…' : 'Cargar más'}
                  </button>
                )}
              </footer>
            </>
          )}
        </section>

        <PublicUrlForm
          busy={busy === 'url'}
          disabled={busy !== null}
          onSubmit={(url) => connectAndScan('url', () => connectSource.connectPublicUrl(url))}
        />
      </div>
    </>
  )
}

function RepoRow({ repo, busy, disabled, onConnect }: { repo: GitHubRepo; busy: boolean; disabled: boolean; onConnect: () => void }) {
  return (
    <li className={cn('flex flex-wrap items-start justify-between gap-x-6 gap-y-3 px-5 py-4', !repo.connectable && 'bg-paper/40')}>
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <a href={repo.url} target="_blank" rel="noreferrer" className="font-mono text-[0.8125rem] font-semibold break-all text-ink hover:text-civic hover:underline">
            {repo.full_name}
          </a>
          {repo.private && (
            <span className="inline-flex items-center gap-1 rounded-xs px-1.5 py-0.5 text-xs font-semibold text-ink-2 ring-1 ring-rule-2 ring-inset">
              <Lock className="size-3" strokeWidth={1.75} aria-hidden="true" />
              Privado
            </span>
          )}
          {repo.archived && (
            <span className="inline-flex items-center gap-1 rounded-xs px-1.5 py-0.5 text-xs font-semibold text-ink-3 ring-1 ring-rule ring-inset">
              <Archive className="size-3" strokeWidth={1.75} aria-hidden="true" />
              Archivado
            </span>
          )}
        </div>
        {repo.description && <p className="max-w-[75ch] text-sm text-ink-2">{repo.description}</p>}
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-3">
          <span className="inline-flex items-center gap-1">
            <GitBranch className="size-3.5" strokeWidth={1.75} aria-hidden="true" />
            <span className="font-mono">{repo.default_branch}</span>
          </span>
          <span className="tabular">{formatSize(repo.size_bytes)}</span>
          {repo.updated_at && <span>Actualizado {formatDateTime(repo.updated_at)}</span>}
        </p>
      </div>

      <div className="flex shrink-0 flex-col items-end gap-1.5">
        {repo.connectable ? (
          <button type="button" onClick={onConnect} disabled={disabled} className={SECONDARY_BUTTON}>
            {busy ? 'Conectando…' : repo.connected ? 'Escanear de nuevo' : 'Conectar y escanear'}
          </button>
        ) : (
          <p className="max-w-[28ch] text-right text-xs text-ink-2">{repo.reason}</p>
        )}
        {repo.connected && <span className="text-xs font-medium text-ok">Conectado</span>}
      </div>
    </li>
  )
}

function PublicUrlForm({ busy, disabled, onSubmit }: { busy: boolean; disabled: boolean; onSubmit: (url: string) => void }) {
  const [url, setUrl] = useState('')
  const [invalid, setInvalid] = useState(false)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!isGitHubUrl(url)) {
      setInvalid(true)
      return
    }
    setInvalid(false)
    onSubmit(url.trim())
  }

  return (
    <section aria-labelledby="public-url-title" className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
      <header className="border-b border-rule px-5 py-3.5">
        <h2 id="public-url-title" className="text-base font-semibold text-ink">
          Repositorio público por URL
        </h2>
      </header>
      <form onSubmit={submit} noValidate className="flex flex-wrap items-start gap-3 px-5 py-4">
        <div className="min-w-0 flex-1 basis-72">
          <label className="relative block">
            <span className="sr-only">URL del repositorio</span>
            <Link2 className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-3" strokeWidth={1.75} aria-hidden="true" />
            <input
              type="url"
              inputMode="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://github.com/organizacion/repositorio"
              aria-invalid={invalid}
              aria-describedby="public-url-help"
              className={cn(INPUT, 'font-mono text-[0.8125rem]', invalid && 'ring-sev-critical')}
            />
          </label>
          <p id="public-url-help" className={cn('mt-1.5 text-xs', invalid ? 'text-sev-critical' : 'text-ink-3')}>
            {invalid ? 'Tiene que ser una URL https://github.com/<dueño>/<repositorio>.' : 'Solo repositorios públicos de GitHub, de hasta 50 MB.'}
          </p>
        </div>
        <button type="submit" disabled={disabled} className={PRIMARY_BUTTON}>
          {busy ? 'Conectando…' : 'Conectar y escanear'}
        </button>
      </form>
    </section>
  )
}

function RepoListSkeleton() {
  return (
    <div role="status" aria-label="Cargando tus repositorios" className="divide-y divide-rule">
      {[0, 1, 2].map((i) => (
        <div key={i} className="space-y-2 px-5 py-4">
          <Skeleton className="h-4 w-64 max-w-full" />
          <Skeleton className="h-3 w-96 max-w-full" />
        </div>
      ))}
    </div>
  )
}
