import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ExecutiveSummaryCard } from './ExecutiveSummaryCard'
import * as summaryData from './summaryData'
import type { ExecutiveSummary } from './types'

const BASE: ExecutiveSummary = {
  scan_id: 'scan_1',
  available: true,
  status: 'at_risk',
  headline: 'Dos riesgos críticos requieren atención inmediata',
  summary: 'El repositorio tiene una clave expuesta.',
  top_risks: [
    { title: 'Clave de AWS expuesta', impact: 'Acceso a la nube', priority: 'inmediata' },
    { title: 'Dependencia vulnerable', impact: 'Exploit público', priority: 'media' },
  ],
  priorities: ['Rotar la clave', 'Actualizar requests'],
  generated_by: 'gemini',
  generated_at: '2026-11-08T12:41:00+00:00',
  triage_status: 'completed',
  triage_reason: null,
}

describe('ExecutiveSummaryCard', () => {
  it('muestra el estado, los riesgos principales y qué hacer primero', async () => {
    vi.spyOn(summaryData, 'loadExecutiveSummary').mockResolvedValue(BASE)
    render(<ExecutiveSummaryCard scanId="scan_1" />)

    expect(await screen.findByText(BASE.headline!)).toBeInTheDocument()
    expect(screen.getByText('Clave de AWS expuesta')).toBeInTheDocument()
    expect(screen.getByText('Prioridad inmediata')).toBeInTheDocument()
    expect(screen.getByText('Rotar la clave')).toBeInTheDocument()
    expect(screen.getByText('Generado con IA')).toBeInTheDocument()
    expect(summaryData.loadExecutiveSummary).toHaveBeenCalledWith('scan_1')
  })

  it('aclara cuando el resumen se armó sin IA y la cuota de Gemini se agotó', async () => {
    vi.spyOn(summaryData, 'loadExecutiveSummary').mockResolvedValue({
      ...BASE,
      generated_by: 'heuristic',
      triage_status: 'quota_exceeded',
    })
    render(<ExecutiveSummaryCard scanId="scan_1" />)

    expect(await screen.findByText('Resumen automático, sin IA')).toBeInTheDocument()
    expect(screen.getByText(/Se agotó la cuota de Gemini/)).toBeInTheDocument()
  })

  it('escaneo sin resumen', async () => {
    vi.spyOn(summaryData, 'loadExecutiveSummary').mockResolvedValue({ ...BASE, available: false, top_risks: [], priorities: [] })
    render(<ExecutiveSummaryCard scanId="scan_1" />)

    expect(await screen.findByText(/se genera al terminar el próximo escaneo/)).toBeInTheDocument()
  })

  it('si falla la carga lo dice sin romper la página', async () => {
    vi.spyOn(summaryData, 'loadExecutiveSummary').mockRejectedValue(new Error('La API respondió con un error (500).'))
    render(<ExecutiveSummaryCard scanId="scan_1" />)

    expect(await screen.findByText(/No pudimos cargar el resumen ejecutivo/)).toBeInTheDocument()
  })

  it('con los datos de ejemplo carga el mock', async () => {
    render(<ExecutiveSummaryCard scanId="scan_demo" />)

    expect(await screen.findByText(/requieren atención inmediata/)).toBeInTheDocument()
    expect(screen.getAllByRole('listitem').length).toBeGreaterThan(3)
  })
})
