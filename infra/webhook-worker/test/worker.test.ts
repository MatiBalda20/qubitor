import { afterEach, describe, expect, it, vi } from 'vitest'
import { signSha256, verifySha256Signature } from '../src/crypto'
import { decidePush } from '../src/github'
import worker, { MAX_BODY_BYTES } from '../src/index'

const GITHUB_SECRET = 'secreto-de-github'
const INTERNAL_SECRET = 'secreto-interno-de-prueba-de-32-caracteres'
const SHA = 'a'.repeat(40)
const DELIVERY = '72d3162e-cc78-11e3-81ab-4c9367dc0958'

class FakeKV {
  store = new Map<string, string>()
  puts: { key: string; ttl?: number }[] = []

  async get(key: string) {
    return this.store.get(key) ?? null
  }

  async put(key: string, value: string, options?: { expirationTtl?: number }) {
    this.store.set(key, value)
    this.puts.push({ key, ttl: options?.expirationTtl })
  }
}

function makeEnv(kv = new FakeKV()) {
  const env = {
    DELIVERIES: kv as unknown as KVNamespace,
    QUBITOR_API_URL: 'https://qubitor-api.onrender.com',
    GITHUB_WEBHOOK_SECRET: GITHUB_SECRET,
    INTERNAL_WEBHOOK_SECRET: INTERNAL_SECRET,
  } satisfies Env
  return { env, kv }
}

function pushPayload(overrides: Record<string, unknown> = {}) {
  return {
    ref: 'refs/heads/main',
    after: SHA,
    deleted: false,
    repository: { html_url: 'https://github.com/acme/demo', default_branch: 'main' },
    ...overrides,
  }
}

async function githubRequest(
  payload: unknown,
  { event = 'push', delivery = DELIVERY, secret = GITHUB_SECRET, path = '/github/webhook', method = 'POST' } = {},
) {
  const body = typeof payload === 'string' ? payload : JSON.stringify(payload)
  const signature = await signSha256(secret, body)
  return new Request(`https://webhooks.qubitor.example${path}`, {
    method,
    body: method === 'GET' ? undefined : body,
    headers: {
      'Content-Type': 'application/json',
      'X-GitHub-Event': event,
      'X-GitHub-Delivery': delivery,
      'X-Hub-Signature-256': `sha256=${signature}`,
    },
  })
}

function mockApi(response: Response | Error = Response.json({ duplicate: false, scans: ['scan-1'], skipped: 0 }, { status: 202 })) {
  const calls: Request[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push(new Request(input, init))
    if (response instanceof Error) throw response
    return response.clone()
  })
  vi.stubGlobal('fetch', fetchMock)
  return calls
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('firma HMAC-SHA256', () => {
  it('coincide con la que calcula Python para la API (vector fijo)', async () => {
    // hmac.new(INTERNAL_SECRET, b'1762650000.{"delivery_id":"abc"}', sha256).hexdigest()
    expect(await signSha256(INTERNAL_SECRET, '1762650000.{"delivery_id":"abc"}')).toBe(
      'add1d4eb3a38c9a1946932af12105b95c87f8cf737b92a6783723bc1e6a2525a',
    )
  })

  it('verifica la firma de GitHub y rechaza las inválidas', async () => {
    const body = new TextEncoder().encode('{"zen":"Keep it logically awesome."}').buffer
    const valid = 'sha256=15153e0cef0b2b637f31c5bed059cd281291ac24656b3bd938ddbebc6f569d8a'

    expect(await verifySha256Signature(GITHUB_SECRET, body, valid)).toBe(true)
    expect(await verifySha256Signature('otro-secreto', body, valid)).toBe(false)
    expect(await verifySha256Signature(GITHUB_SECRET, body, 'sha256=' + '0'.repeat(64))).toBe(false)
    expect(await verifySha256Signature(GITHUB_SECRET, body, 'sha1=abc')).toBe(false)
    expect(await verifySha256Signature(GITHUB_SECRET, body, 'sha256=zz')).toBe(false)
    expect(await verifySha256Signature(GITHUB_SECRET, body, null)).toBe(false)
    expect(await verifySha256Signature('', body, valid)).toBe(false)
  })
})

describe('qué push dispara un escaneo', () => {
  it('push a la rama por defecto', () => {
    expect(decidePush(pushPayload())).toEqual({
      scan: { repositoryUrl: 'https://github.com/acme/demo', commitSha: SHA, ref: 'refs/heads/main' },
    })
  })

  it.each([
    [{ ref: 'refs/heads/feature/x' }, 'no es la rama por defecto'],
    [{ ref: 'refs/tags/v1.0' }, 'no es la rama por defecto'],
    [{ deleted: true }, 'se borró la rama'],
    [{ after: '0'.repeat(40) }, 'se borró la rama'],
    [{ after: 'no-es-un-sha' }, 'commit inválido'],
    [{ repository: { html_url: 'https://gitlab.com/a/b', default_branch: 'main' } }, 'repositorio inválido'],
    [{ repository: { html_url: 'https://github.com/a/../b', default_branch: 'main' } }, 'repositorio inválido'],
    [{ repository: null }, 'repositorio inválido'],
  ])('ignora %o', (overrides, reason) => {
    expect(decidePush(pushPayload(overrides))).toEqual({ ignore: reason })
  })

  it('ignora payloads que no son objetos', () => {
    expect(decidePush('texto')).toEqual({ ignore: 'payload inválido' })
  })
})

describe('worker', () => {
  it('pide el escaneo a la API firmado y marca la entrega', async () => {
    const calls = mockApi()
    const { env, kv } = makeEnv()

    const response = await worker.fetch(await githubRequest(pushPayload()), env)

    expect(response.status).toBe(202)
    expect(await response.json()).toEqual({ accepted: true, scans: ['scan-1'], duplicate: false })
    expect(calls).toHaveLength(1)
    const call = calls[0]
    expect(call.url).toBe('https://qubitor-api.onrender.com/internal/github/push')
    const body = await call.text()
    expect(JSON.parse(body)).toEqual({
      delivery_id: DELIVERY,
      repository_url: 'https://github.com/acme/demo',
      commit_sha: SHA,
      ref: 'refs/heads/main',
    })
    const timestamp = call.headers.get('X-Qubitor-Timestamp')!
    expect(call.headers.get('X-Qubitor-Signature')).toBe(`sha256=${await signSha256(INTERNAL_SECRET, `${timestamp}.${body}`)}`)
    // Ningún secreto viaja en el pedido.
    expect(body).not.toContain(INTERNAL_SECRET)
    expect([...call.headers.values()].join(' ')).not.toContain(INTERNAL_SECRET)
    expect(kv.puts).toEqual([{ key: `delivery:${DELIVERY}`, ttl: 86400 }])
  })

  it('responde ping sin llamar a la API', async () => {
    const calls = mockApi()

    const response = await worker.fetch(await githubRequest({ zen: 'hola' }, { event: 'ping' }), makeEnv().env)

    expect(response.status).toBe(200)
    expect(calls).toHaveLength(0)
  })

  it('rechaza una firma inválida antes de mirar el evento', async () => {
    const calls = mockApi()

    const response = await worker.fetch(await githubRequest(pushPayload(), { secret: 'otro' }), makeEnv().env)

    expect(response.status).toBe(401)
    expect(calls).toHaveLength(0)
  })

  it('rechaza un pedido sin firma', async () => {
    const request = new Request('https://w.example/github/webhook', {
      method: 'POST',
      body: JSON.stringify(pushPayload()),
      headers: { 'X-GitHub-Event': 'push', 'X-GitHub-Delivery': DELIVERY },
    })

    expect((await worker.fetch(request, makeEnv().env)).status).toBe(401)
  })

  it('no vuelve a pedir el escaneo de una entrega repetida', async () => {
    const calls = mockApi()
    const { env } = makeEnv()

    await worker.fetch(await githubRequest(pushPayload()), env)
    const second = await worker.fetch(await githubRequest(pushPayload()), env)

    expect(second.status).toBe(200)
    expect(await second.json()).toEqual({ duplicate: true })
    expect(calls).toHaveLength(1)
  })

  it('ignora otros eventos y pushes a otras ramas', async () => {
    const calls = mockApi()
    const { env } = makeEnv()

    const issues = await worker.fetch(await githubRequest({ action: 'opened' }, { event: 'issues' }), env)
    const branch = await worker.fetch(await githubRequest(pushPayload({ ref: 'refs/heads/dev' })), env)

    expect(issues.status).toBe(202)
    expect(branch.status).toBe(202)
    expect(calls).toHaveLength(0)
  })

  it('si la API falla responde 502 y no marca la entrega, así GitHub puede reenviarla', async () => {
    mockApi(new Response('error', { status: 503 }))
    const { env, kv } = makeEnv()

    const response = await worker.fetch(await githubRequest(pushPayload()), env)

    expect(response.status).toBe(502)
    expect(kv.puts).toHaveLength(0)
  })

  it('si la API no responde devuelve 502', async () => {
    mockApi(new TypeError('network'))

    expect((await worker.fetch(await githubRequest(pushPayload()), makeEnv().env)).status).toBe(502)
  })

  it('rechaza cuerpos demasiado grandes sin leerlos enteros', async () => {
    const calls = mockApi()
    const huge = 'x'.repeat(MAX_BODY_BYTES + 1)

    const response = await worker.fetch(await githubRequest(huge), makeEnv().env)

    expect(response.status).toBe(413)
    expect(calls).toHaveLength(0)
  })

  it('rechaza JSON inválido aunque esté firmado', async () => {
    expect((await worker.fetch(await githubRequest('{no json'), makeEnv().env)).status).toBe(400)
  })

  it('exige un X-GitHub-Delivery válido', async () => {
    expect((await worker.fetch(await githubRequest(pushPayload(), { delivery: '../x' }), makeEnv().env)).status).toBe(400)
  })

  it('solo atiende POST en la ruta del webhook', async () => {
    expect((await worker.fetch(new Request('https://w.example/otra', { method: 'POST' }), makeEnv().env)).status).toBe(404)
    expect((await worker.fetch(new Request('https://w.example/github/webhook'), makeEnv().env)).status).toBe(405)
  })
})
