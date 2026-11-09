import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, request, setTokenGetter } from './api'

afterEach(() => {
  setTokenGetter(async () => null)
})

describe('request', () => {
  it('adjunta el JWT de Clerk y manda JSON', async () => {
    const fetchMock = vi.fn(async () => Response.json({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    setTokenGetter(async () => 'jwt-de-prueba')

    await request('/github/repositories', { method: 'POST', body: JSON.stringify({ full_name: 'a/b' }) })

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    const headers = new Headers(init.headers)
    expect(headers.get('Authorization')).toBe('Bearer jwt-de-prueba')
    expect(headers.get('Content-Type')).toBe('application/json')
    vi.unstubAllGlobals()
  })

  it('convierte el detail de FastAPI en ApiError con su código', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ detail: 'Conectá tu cuenta de GitHub' }, { status: 409 })))

    await expect(request('/github/repositories')).rejects.toEqual(new ApiError(409, 'Conectá tu cuenta de GitHub'))
    vi.unstubAllGlobals()
  })
})
