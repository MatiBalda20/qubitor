import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as dataSource from './dataSource'
import type { OrganizationData } from './dataSource'
import OrganizationPage from './OrganizationPage'

const MIEMBRO: OrganizationData = {
  me: {
    user_id: 'u_2',
    role: 'member',
    organization: { id: 'org_1', name: 'acme', personal: false },
    permissions: { connect_repositories: false, start_scans: true, update_findings: true },
  },
  members: [
    { user_id: 'u_1', name: 'Ana Gómez', image_url: null, role: 'admin', joined_at: null, last_seen_at: '2026-11-17T18:20:00Z', is_you: false },
    { user_id: 'u_2', name: null, image_url: null, role: 'member', joined_at: null, last_seen_at: null, is_you: true },
  ],
}

describe('OrganizationPage', () => {
  it('muestra el rol, qué puede hacer y los miembros', async () => {
    vi.spyOn(dataSource, 'loadOrganization').mockResolvedValue(MIEMBRO)
    render(<OrganizationPage />)

    const rol = await screen.findByRole('region', { name: 'Tu rol' })
    expect(within(rol).getByText('Miembro')).toBeInTheDocument()
    expect(within(rol).getByText(/Conectar repositorios lo hace un admin/)).toBeInTheDocument()
    const conectar = within(rol).getByText('Conectar repositorios').closest('div')!
    expect(within(conectar).getByText('No')).toBeInTheDocument()
    const escanear = within(rol).getByText('Lanzar escaneos').closest('div')!
    expect(within(escanear).getByText('Sí')).toBeInTheDocument()

    const miembros = screen.getByRole('region', { name: 'Miembros' })
    const filas = within(miembros).getAllByRole('listitem')
    expect(filas).toHaveLength(2)
    expect(within(filas[0]).getByText('Ana Gómez')).toBeInTheDocument()
    expect(within(filas[0]).getByText('Admin')).toBeInTheDocument()
    expect(within(filas[1]).getByText('Usuario sin nombre')).toBeInTheDocument()
    expect(within(filas[1]).getByText('(vos)')).toBeInTheDocument()
    expect(screen.getByText('acme')).toBeInTheDocument()
  })

  it('en el espacio personal es admin', async () => {
    vi.spyOn(dataSource, 'loadOrganization').mockResolvedValue({
      me: { ...MIEMBRO.me, role: 'admin', organization: { id: 'p', name: 'Personal', personal: true }, permissions: { connect_repositories: true, start_scans: true, update_findings: true } },
      members: [{ ...MIEMBRO.members[1], role: 'admin' }],
    })
    render(<OrganizationPage />)

    expect(await screen.findByText('Tu espacio personal')).toBeInTheDocument()
    expect(screen.getByText(/En tu espacio personal sos admin/)).toBeInTheDocument()
  })

  it('si falla la API ofrece reintentar', async () => {
    vi.spyOn(dataSource, 'loadOrganization').mockRejectedValue(new Error('La API respondió con un error (500).'))
    render(<OrganizationPage />)

    expect(await screen.findByText('No pudimos cargar la organización')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })
})
