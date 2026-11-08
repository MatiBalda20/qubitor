/**
 * Copia en TypeScript del contrato común de backend/app/engines/base.py.
 * Si cambia base.py, este archivo se actualiza en el mismo Pull Request.
 */

/** Escala de severidad unificada (sección 3 del plan de desarrollo). */
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

/** Nombre de cada motor, tal como lo usa Finding.engine. */
export type EngineName = 'sast' | 'sca' | 'secrets' | 'crypto'

/** Un hallazgo de un motor, igual al dataclass Finding de base.py. */
export interface Finding {
  engine: EngineName
  /** ej. "crypto.classic.weak-hash.md5" */
  rule_id: string
  /** texto corto para el dashboard */
  title: string
  severity: Severity
  /** relativo a la raíz del repo */
  file_path: string
  line: number | null
  /** máx. 5 líneas, con los secretos ya enmascarados */
  snippet: string
  description: string
  /** ej. "CWE-327" */
  cwe: string | null
  /** solo SCA */
  cve: string | null
  metadata: Record<string, unknown>
}

/**
 * Lo que agrega la API sobre el contrato: identidad, estado y triage con IA.
 * Provisorio hasta que el Módulo A publique los modelos de /scans/{id}/findings.
 */
export type FindingStatus = 'open' | 'resolved' | 'false_positive'

/** Respuesta del triage con Gemini (response_schema del plan, Módulo E). */
export interface AiTriage {
  is_false_positive: boolean
  adjusted_severity: Severity
  /** para el líder técnico */
  explanation: string
  /** pasos concretos */
  remediation: string
}

export interface FindingRecord extends Finding {
  id: string
  scan_id: string
  /** hash de motor + regla + archivo + línea */
  fingerprint: string
  status: FindingStatus
  triage: AiTriage | null
}

export const SEVERITIES: readonly Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export const ENGINES: readonly EngineName[] = ['sast', 'sca', 'secrets', 'crypto']
