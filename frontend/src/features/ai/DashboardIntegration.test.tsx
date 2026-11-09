import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ToastProvider } from '@/components/toast/ToastProvider'
import DashboardPage from '@/features/dashboard/DashboardPage'

describe('dashboard general con el resumen ejecutivo', () => {
  it('muestra la tarjeta del Módulo E arriba del dashboard', async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <DashboardPage />
        </ToastProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { name: 'Resumen ejecutivo' })).toBeInTheDocument()
    expect(await screen.findByText(/requieren atención inmediata/)).toBeInTheDocument()
  })
})
