/** Respuesta de GET /scans/{id}/summary (backend/app/ai/routes.py). */
export type SummaryStatus = 'good' | 'acceptable' | 'at_risk' | 'critical'

export type RiskPriority = 'inmediata' | 'alta' | 'media'

/** Cómo terminó el triage del escaneo. */
export type TriageStatus = 'completed' | 'partial' | 'quota_exceeded' | 'unavailable' | 'disabled' | 'skipped'

export interface ExecutiveRisk {
  title: string
  impact: string
  priority: RiskPriority
}

export interface ExecutiveSummary {
  scan_id: string
  /** False mientras el escaneo no tiene resumen. */
  available: boolean
  status: SummaryStatus | null
  headline: string | null
  summary: string | null
  top_risks: ExecutiveRisk[]
  priorities: string[]
  generated_by: 'gemini' | 'heuristic' | null
  generated_at: string | null
  triage_status: TriageStatus | null
  triage_reason: string | null
}
