import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/components/toast/ToastProvider'
import { ApiError } from '@/lib/api'
import ConnectPage from './ConnectPage'
import { connectSource } from './dataSource'

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <ConnectPage />
      </ToastProvider>
    </MemoryRouter>,
  )
}

describe('ConnectPage', () => {
  it('lista los repos de GitHub y marca los ya conectados', async () => {
    renderPage()

    expect(await screen.findByText('qubitor-org/api-pagos')).toBeInTheDocument()
    const demo = screen.getByText('qubitor-org/qubitor-demo-vulnerable').closest('li')!
    expect(within(demo).getByText('Conectado')).toBeInTheDocument()
    expect(within(demo).getByRole('button', { name: 'Escanear de nuevo' })).toBeInTheDocument()
  })

  it('explica por qué un repo no se puede conectar', async () => {
    renderPage()

    const privado = (await screen.findByText('qubitor-org/panel-administracion')).closest('li')!
    expect(within(privado).getByText('Privado')).toBeInTheDocument()
    expect(within(privado).getByText(/privados todavía no están habilitados/)).toBeInTheDocument()
    expect(within(privado).queryByRole('button')).not.toBeInTheDocument()
  })

  it('busca entre los repos cargados', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('qubitor-org/api-pagos')

    await user.type(screen.getByRole('searchbox', { name: 'Buscar repositorio' }), 'pagos')

    expect(screen.getByText('qubitor-org/api-pagos')).toBeInTheDocument()
    expect(screen.queryByText('qubitor-org/landing')).not.toBeInTheDocument()
  })

  it('carga la página siguiente', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('qubitor-org/api-pagos')

    await user.click(screen.getByRole('button', { name: 'Cargar más' }))

    expect(await screen.findByText('qubitor-org/scripts-legacy')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cargar más' })).not.toBeInTheDocument()
    expect(screen.getByText(/El repositorio supera el límite de 50 MB/)).toBeInTheDocument()
  })

  it('conecta un repo y lanza el primer escaneo', async () => {
    const user = userEvent.setup()
    const connect = vi.spyOn(connectSource, 'connectGitHubRepo')
    const start = vi.spyOn(connectSource, 'startScan')
    renderPage()
    const fila = (await screen.findByText('qubitor-org/landing')).closest('li')!

    await user.click(within(fila).getByRole('button', { name: 'Conectar y escanear' }))

    await waitFor(() => expect(start).toHaveBeenCalledWith('repo_landing'))
    expect(connect).toHaveBeenCalledWith('qubitor-org/landing')
    expect(await screen.findByRole('region', { name: 'Progreso del escaneo' })).toBeInTheDocument()
    expect(await screen.findByText(/Ver los resultados de qubitor-org\/landing/)).toBeInTheDocument()
  })

  it('valida la URL pública antes de enviarla', async () => {
    const user = userEvent.setup()
    const connect = vi.spyOn(connectSource, 'connectPublicUrl')
    renderPage()
    await screen.findByText('qubitor-org/api-pagos')
    const form = screen.getByRole('region', { name: 'Repositorio público por URL' })
    const input = within(form).getByRole('textbox', { name: 'URL del repositorio' })

    await user.type(input, 'https://gitlab.com/a/b')
    await user.click(within(form).getByRole('button', { name: 'Conectar y escanear' }))

    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(connect).not.toHaveBeenCalled()

    await user.clear(input)
    await user.type(input, 'https://github.com/octocat/Hello-World')
    await user.click(within(form).getByRole('button', { name: 'Conectar y escanear' }))

    await waitFor(() => expect(connect).toHaveBeenCalledWith('https://github.com/octocat/Hello-World'))
  })

  it('si GitHub no está vinculado lo explica y permite reintentar', async () => {
    const user = userEvent.setup()
    vi.spyOn(connectSource, 'listGitHubRepos').mockRejectedValueOnce(
      new ApiError(409, 'Conectá tu cuenta de GitHub para ver tus repositorios'),
    )
    renderPage()

    expect(await screen.findByText('Tu cuenta de GitHub no está vinculada')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('qubitor-org/api-pagos')).toBeInTheDocument()
  })

  it('muestra el error de la API cuando no puede traer los repos', async () => {
    vi.spyOn(connectSource, 'listGitHubRepos').mockRejectedValueOnce(new ApiError(503, 'No se pudo consultar GitHub'))
    renderPage()

    expect(await screen.findByText('No pudimos traer tus repositorios')).toBeInTheDocument()
    expect(screen.getByText('No se pudo consultar GitHub')).toBeInTheDocument()
  })

  it('avisa con un toast si falla la conexión', async () => {
    const user = userEvent.setup()
    vi.spyOn(connectSource, 'connectGitHubRepo').mockRejectedValueOnce(new ApiError(422, 'El repositorio supera el límite de 50 MB'))
    renderPage()
    const fila = (await screen.findByText('qubitor-org/landing')).closest('li')!

    await user.click(within(fila).getByRole('button', { name: 'Conectar y escanear' }))

    expect(await screen.findByText('El repositorio supera el límite de 50 MB')).toBeInTheDocument()
  })
})
