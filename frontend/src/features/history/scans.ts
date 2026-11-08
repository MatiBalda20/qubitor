import type { Grade, ScanStatus } from '@/types/Scan'
import type { HistoryScan } from './dataSource'

export const SCAN_STATUS_LABEL: Record<ScanStatus, string> = {
  queued: 'En cola',
  running: 'Escaneando',
  completed: 'Completado',
  failed: 'Falló',
}

/** Mismos tonos que la nota del dashboard: verde aprobado o la severidad que la explica. */
export const GRADE_TEXT: Record<Grade, string> = {
  A: 'text-ok',
  B: 'text-ok',
  C: 'text-sev-medium-ink',
  D: 'text-sev-high-ink',
  F: 'text-sev-critical',
}

export interface HistoryRow {
  scan: HistoryScan
  /** Diferencia de Risk Score con el escaneo completado anterior; null si no hay con qué comparar. */
  delta: number | null
}

/**
 * Arma las filas del historial. Cada escaneo completado se compara con el
 * completado anterior, salteando los fallidos y los que siguen en curso.
 */
export function historyRows(scans: readonly HistoryScan[]): HistoryRow[] {
  return scans.map((scan, index) => {
    if (scan.status !== 'completed' || scan.risk_score === null) return { scan, delta: null }
    const previous = scans
      .slice(index + 1)
      .find((s) => s.status === 'completed' && s.risk_score !== null)
    return { scan, delta: previous ? round1(scan.risk_score - previous.risk_score!) : null }
  })
}

/** Resumen para el encabezado: último Risk Score y su cambio desde el primero del historial. */
export function scoreTrend(scans: readonly HistoryScan[]): { latest: number; first: number } | null {
  const completed = scans.filter((s) => s.status === 'completed' && s.risk_score !== null)
  if (completed.length < 2) return null
  return { latest: completed[0].risk_score!, first: completed[completed.length - 1].risk_score! }
}

function round1(value: number): number {
  return Math.round(value * 10) / 10
}
