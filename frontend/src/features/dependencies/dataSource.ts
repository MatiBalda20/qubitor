import { api } from '@/lib/api'
import { USE_MOCKS } from '@/lib/config'
import type { FindingRecord } from '@/types/Finding'
import type { Repository, Scan } from '@/types/Scan'
import mock from './mock.json'

export interface DependenciesData {
  repository: Repository
  /** Último escaneo terminado; null si el repo todavía no se escaneó. */
  scan: Scan | null
  /** Solo los hallazgos del motor SCA. */
  findings: FindingRecord[]
}

const MOCK_LATENCY_MS = 350

/** Devuelve null cuando la organización no conectó ningún repositorio. */
export async function loadDependencies(): Promise<DependenciesData | null> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS))
    return structuredClone({
      repository: mock.repository as Repository,
      scan: mock.scan as Scan,
      findings: mock.findings as FindingRecord[],
    })
  }

  const [repository] = await api.listRepositories()
  if (!repository) return null
  const history = await api.repositoryHistory(repository.id)
  const scan = history.find((s) => s.status === 'completed') ?? null
  const findings = scan ? await api.getScanFindings(scan.id) : []
  return { repository, scan, findings: findings.filter((f) => f.engine === 'sca') }
}
