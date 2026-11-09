import { request } from '@/lib/api'
import { USE_MOCKS } from '@/lib/config'
import mock from './mock.json'
import type { ExecutiveSummary } from './types'

const MOCK_LATENCY_MS = 300

/** Resumen ejecutivo de un escaneo: la API real o el mock.json. */
export async function loadExecutiveSummary(scanId: string): Promise<ExecutiveSummary> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS))
    return { ...(structuredClone(mock.summary) as ExecutiveSummary), scan_id: scanId }
  }
  return request<ExecutiveSummary>(`/scans/${encodeURIComponent(scanId)}/summary`)
}
