import type { EngineName, FindingRecord, FindingStatus, Severity } from '@/types/Finding'
import type { ScanStage } from '@/types/Scan'

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Crítica',
  high: 'Alta',
  medium: 'Media',
  low: 'Baja',
  info: 'Info',
}

export const ENGINE_LABEL: Record<EngineName, string> = {
  sast: 'SAST',
  sca: 'Dependencias',
  secrets: 'Secretos',
  crypto: 'Criptografía',
}

export const STATUS_LABEL: Record<FindingStatus, string> = {
  open: 'Abierto',
  resolved: 'Resuelto',
  false_positive: 'Falso positivo',
}

export const STAGE_LABEL: Record<ScanStage, string> = {
  clone: 'Clonado',
  engines: 'Motores',
  normalize: 'Normalización',
  triage: 'Triage con IA',
  score: 'Risk Score',
  persist: 'Guardado',
}

/** Vistas de cada módulo. El dashboard enlaza a ellas. */
export type ModuleView = 'code' | 'secrets' | 'pqc' | 'dependencies'

export const MODULE_VIEWS: readonly {
  id: ModuleView
  path: string
  label: string
  owner: string
  scope: string
}[] = [
  { id: 'code', path: '/code', label: 'Código inseguro', owner: 'Módulo C', scope: 'SAST y criptografía clásica' },
  { id: 'secrets', path: '/secrets', label: 'Secretos', owner: 'Módulo C', scope: 'Credenciales expuestas' },
  { id: 'pqc', path: '/pqc', label: 'Preparación post-cuántica', owner: 'Módulo D', scope: 'Shor, Grover e inventario' },
  { id: 'dependencies', path: '/dependencies', label: 'Dependencias', owner: 'Módulo D', scope: 'CVE en paquetes (OSV)' },
]

/** A qué vista pertenece un hallazgo, según el motor y el prefijo de la regla. */
export function viewOf(finding: Pick<FindingRecord, 'engine' | 'rule_id'>): ModuleView {
  switch (finding.engine) {
    case 'sca':
      return 'dependencies'
    case 'secrets':
      return 'secrets'
    case 'crypto':
      return finding.rule_id.startsWith('crypto.pqc.') ? 'pqc' : 'code'
    case 'sast':
      return 'code'
  }
}
