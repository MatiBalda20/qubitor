import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FindingCard } from '@/components/FindingCard'
import type { FindingRecord } from '@/types/Finding'
import { AiTriagePanel } from './AiTriagePanel'
import { remediationSteps } from './remediation'

function finding(overrides: Partial<FindingRecord> = {}): FindingRecord {
  return {
    id: 'f1',
    scan_id: 's1',
    fingerprint: 'fp1',
    engine: 'sast',
    rule_id: 'sast.bandit.B608',
    title: 'Consulta SQL armada con strings',
    severity: 'high',
    file_path: 'app/db.py',
    line: 12,
    snippet: 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")',
    description: 'Posible inyección SQL.',
    cwe: 'CWE-89',
    cve: null,
    metadata: {},
    status: 'open',
    triage: {
      is_false_positive: false,
      adjusted_severity: 'critical',
      explanation: 'El id llega de la URL sin validar: permite leer toda la tabla.',
      remediation: '1. Usar una consulta parametrizada.\n2. Validar que user_id sea numérico.',
    },
    ...overrides,
  }
}

describe('remediationSteps', () => {
  it('separa pasos numerados o con guiones', () => {
    expect(remediationSteps('1. Uno\n2) Dos\n- Tres\n• Cuatro')).toEqual(['Uno', 'Dos', 'Tres', 'Cuatro'])
  })

  it('un párrafo queda como un solo paso y lo vacío no genera pasos', () => {
    expect(remediationSteps('Rotar la clave en AWS.')).toEqual(['Rotar la clave en AWS.'])
    expect(remediationSteps('  \n ')).toEqual([])
    expect(remediationSteps(null)).toEqual([])
  })
})

describe('AiTriagePanel', () => {
  it('muestra la explicación y la remediación como pasos', () => {
    render(<AiTriagePanel finding={finding()} />)

    expect(screen.getByRole('region', { name: 'Evaluación de la IA' })).toBeInTheDocument()
    expect(screen.getByText(/permite leer toda la tabla/)).toBeInTheDocument()
    const pasos = screen.getAllByRole('listitem')
    expect(pasos.map((p) => p.textContent)).toEqual(['Usar una consulta parametrizada.', 'Validar que user_id sea numérico.'])
  })

  it('muestra el cambio de severidad motor → IA', () => {
    render(<AiTriagePanel finding={finding()} />)

    expect(screen.getByText('Severidad del motor')).toBeInTheDocument()
    expect(screen.getByText('según la IA')).toBeInTheDocument()
  })

  it('marca los posibles falsos positivos y explica que no cuentan', () => {
    render(<AiTriagePanel finding={finding({ triage: { ...finding().triage!, is_false_positive: true } })} />)

    expect(screen.getByText('Posible falso positivo')).toBeInTheDocument()
    expect(screen.getByText(/No cuenta para el Risk Score/)).toBeInTheDocument()
  })

  it('sin triage no muestra nada', () => {
    const { container } = render(<AiTriagePanel finding={finding({ triage: null })} />)

    expect(container).toBeEmptyDOMElement()
  })

  it('FindingCard lo usa sin repetir la severidad del motor', () => {
    render(<FindingCard finding={finding()} />)

    expect(screen.getByRole('region', { name: 'Evaluación de la IA' })).toBeInTheDocument()
    expect(screen.queryByText('según la IA')).not.toBeInTheDocument()
    // La severidad del motor la sigue mostrando FindingCard en sus datos.
    expect(screen.getByText('Severidad del motor')).toBeInTheDocument()
  })

  it('el texto de la IA se muestra escapado, nunca como HTML', () => {
    const html = '<img src=x onerror="alert(1)">'
    render(<AiTriagePanel finding={finding({ triage: { ...finding().triage!, explanation: html } })} />)

    expect(screen.getByText(html)).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
  })
})
