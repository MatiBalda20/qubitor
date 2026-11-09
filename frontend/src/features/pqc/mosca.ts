import { shorUse, type CryptoUsage } from './quantum'

/**
 * Desigualdad de Mosca: si X + Y > Z, lo que protege esa criptografía ya está
 * en riesgo hoy, aunque la computadora cuántica todavía no exista.
 *
 * X: años que tiene que seguir protegido (datos secretos o firmas válidas).
 * Y: años que lleva migrar a criptografía post-cuántica.
 * Z: años hasta que exista una computadora cuántica capaz de romperla.
 */
export interface MoscaParams {
  /** X para lo que cifra o acuerda claves: años que los datos tienen que seguir secretos. */
  dataYears: number
  /** X para las firmas: años que una firma tiene que seguir siendo confiable. */
  signatureYears: number
  /** Y: años para migrar. */
  migrationYears: number
  /** Z: años hasta una computadora cuántica relevante. */
  quantumYears: number
}

/** Año en que NIST deja de permitir RSA y curvas elípticas (NIST IR 8547). Referencia para Z. */
export const NIST_DISALLOW_YEAR = 2035

export const MAX_YEARS = 50

export function defaultMoscaParams(today: Date = new Date()): MoscaParams {
  return {
    dataYears: 10,
    signatureYears: 2,
    migrationYears: 5,
    quantumYears: Math.max(1, NIST_DISALLOW_YEAR - today.getFullYear()),
  }
}

/** data: cifra o acuerda claves («cosechar ahora, descifrar después») · signature: firma. */
export type MoscaGroup = 'data' | 'signature'

export interface MoscaVerdict {
  group: MoscaGroup
  /** X del grupo. */
  shelfLife: number
  /** X + Y. */
  total: number
  /** Z − (X + Y): negativo si ya está en riesgo. */
  margin: number
  atRisk: boolean
  usages: CryptoUsage[]
}

/** Un veredicto por grupo con usos activos vulnerables a Shor. */
export function moscaAssessment(usages: readonly CryptoUsage[], params: MoscaParams): MoscaVerdict[] {
  const groups: Record<MoscaGroup, CryptoUsage[]> = { data: [], signature: [] }
  for (const usage of usages) {
    if (!usage.active) continue
    const use = shorUse(usage)
    // Si no se sabe para qué se usa la clave, se toma el caso más exigente: que cifre datos.
    if (use) groups[use === 'signature' ? 'signature' : 'data'].push(usage)
  }

  return (['data', 'signature'] as const)
    .filter((group) => groups[group].length > 0)
    .map((group) => {
      const shelfLife = group === 'data' ? params.dataYears : params.signatureYears
      const total = shelfLife + params.migrationYears
      return {
        group,
        shelfLife,
        total,
        margin: params.quantumYears - total,
        atRisk: total > params.quantumYears,
        usages: groups[group],
      }
    })
}

/** Ids de los hallazgos que ya están en riesgo según Mosca. */
export function atRiskIds(verdicts: readonly MoscaVerdict[]): Set<string> {
  return new Set(verdicts.filter((v) => v.atRisk).flatMap((v) => v.usages.map((u) => u.finding.id)))
}

/** Años enteros entre 0 y MAX_YEARS; lo que no es un número queda en 0. */
export function clampYears(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(MAX_YEARS, Math.max(0, Math.round(value)))
}
