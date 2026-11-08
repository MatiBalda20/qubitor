import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import type { Scan } from '@/types/Scan'

interface ScanPollingOptions {
  /** Cómo se lee el escaneo; por defecto GET /scans/{id}. Los mocks pasan el suyo. */
  fetchScan?: (scanId: string) => Promise<Scan>
  intervalMs?: number
  /** Se llama una vez cuando el escaneo termina (done o failed). */
  onFinish?: (scan: Scan) => void
}

const FINISHED: ReadonlySet<Scan['status']> = new Set(['done', 'failed'])

/**
 * Consulta /scans/{id} cada `intervalMs` hasta que el escaneo termina.
 * Con scanId null no hace nada.
 */
export function useScanPolling(scanId: string | null, options: ScanPollingOptions = {}) {
  const { fetchScan = api.getScan, intervalMs = 1500 } = options
  const [scan, setScan] = useState<Scan | null>(null)
  const [error, setError] = useState<string | null>(null)

  // onFinish en una ref para no reiniciar el polling si cambia la función.
  const onFinish = useRef(options.onFinish)
  useEffect(() => {
    onFinish.current = options.onFinish
  })

  useEffect(() => {
    if (scanId === null) return
    let cancelled = false
    let timer: number | undefined

    async function tick(id: string) {
      try {
        const next = await fetchScan(id)
        if (cancelled) return
        setScan(next)
        setError(null)
        if (FINISHED.has(next.status)) {
          onFinish.current?.(next)
          return
        }
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'No se pudo consultar el escaneo.')
      }
      timer = window.setTimeout(() => tick(id), intervalMs)
    }

    tick(scanId)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [scanId, fetchScan, intervalMs])

  return { scan: scanId === null ? null : scan, error }
}
