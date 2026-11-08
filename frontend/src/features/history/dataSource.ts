import { api } from '@/lib/api'
import { USE_MOCKS } from '@/lib/config'
import type { Repository, Scan } from '@/types/Scan'
import mock from './mock.json'

/**
 * Lo que /history agrega a un escaneo: qué motores fallaron en uno que terminó
 * igual, y cuántos hallazgos aparecieron o dejaron de aparecer respecto del
 * completado anterior (null si no hay con qué comparar).
 */
export type HistoryScan = Scan & {
  engine_errors?: Record<string, string> | null
  new_findings?: number | null
  resolved_findings?: number | null
}

export interface HistoryData {
  repository: Repository
  /** Del más nuevo al más viejo, como los devuelve /repositories/{id}/history. */
  scans: HistoryScan[]
}

const MOCK_LATENCY_MS = 350

/** Devuelve null cuando la organización no conectó ningún repositorio. */
export async function loadHistory(): Promise<HistoryData | null> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS))
    return structuredClone({
      repository: mock.repository as Repository,
      scans: mock.scans as HistoryScan[],
    })
  }

  const [repository] = await api.listRepositories()
  if (!repository) return null
  const scans: HistoryScan[] = await api.repositoryHistory(repository.id)
  return { repository, scans }
}
