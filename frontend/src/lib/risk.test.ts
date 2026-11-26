import { describe, expect, it } from 'vitest'
import type { FindingRecord } from '@/types/Finding'
import { countsTowardScore, gradeFor, riskScore } from './risk'

function finding(overrides: Partial<FindingRecord> = {}): FindingRecord {
  return {
    id: 'f1',
    scan_id: 's1',
    fingerprint: 'fp1',
    engine: 'sast',
    rule_id: 'sast.eval',
    title: 'Uso de eval',
    severity: 'high',
    file_path: 'app/main.py',
    line: 1,
    snippet: 'eval(x)',
    description: '',
    cwe: null,
    cve: null,
    metadata: {},
    status: 'open',
    triage: null,
    ...overrides,
  }
}

describe('riskScore', () => {
  it('un falso positivo sugerido por la IA sigue penalizando hasta que una persona lo marque', () => {
    const sugerido = finding({
      triage: { is_false_positive: true, adjusted_severity: 'high', explanation: 'e', remediation: 'r' },
    })

    expect(countsTowardScore(sugerido)).toBe(true)
    expect(riskScore([sugerido])).toBe(95)
    expect(riskScore([{ ...sugerido, status: 'false_positive' }])).toBe(100)
  })

  it('usa la severidad ajustada por la IA y no cuenta los info', () => {
    const ajustado = finding({
      triage: { is_false_positive: false, adjusted_severity: 'critical', explanation: 'e', remediation: 'r' },
    })
    const inventario = finding({ id: 'f2', severity: 'info' })

    expect(riskScore([ajustado, inventario])).toBe(90)
    expect(gradeFor(90)).toBe('A')
  })
})
