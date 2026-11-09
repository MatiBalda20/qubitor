/**
 * Worker de webhooks de GitHub (Módulo E).
 *
 * 1. Verifica la firma HMAC-SHA256 de GitHub (`X-Hub-Signature-256`).
 * 2. Responde `ping`; ignora todo evento que no sea `push` a la rama por defecto.
 * 3. Descarta entregas repetidas (`X-GitHub-Delivery`) con KV.
 * 4. Pide el escaneo a la API de Qubitor (`POST /internal/github/push`), firmado con
 *    INTERNAL_WEBHOOK_SECRET. La API encola el trabajo en la cola del Módulo A: el
 *    Worker no tiene acceso a Redis.
 */

import { BodyTooLarge, readBodyLimited } from './body'
import { signSha256, verifySha256Signature } from './crypto'
import { decidePush, isValidDeliveryId, type PushToScan } from './github'

export const WEBHOOK_PATH = '/github/webhook'
export const MAX_BODY_BYTES = 2 * 1024 * 1024
export const DELIVERY_TTL_SECONDS = 24 * 60 * 60
export const API_TIMEOUT_MS = 10_000

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return handleRequest(request, env)
  },
} satisfies ExportedHandler<Env>

export async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url)
  if (url.pathname !== WEBHOOK_PATH) return json({ error: 'No encontrado' }, 404)
  if (request.method !== 'POST') return json({ error: 'Método no permitido' }, 405, { Allow: 'POST' })

  let body: ArrayBuffer
  try {
    body = await readBodyLimited(request, MAX_BODY_BYTES)
  } catch (error) {
    if (error instanceof BodyTooLarge) return json({ error: 'El cuerpo es demasiado grande' }, 413)
    throw error
  }

  // La firma se verifica antes de mirar cualquier otro dato del pedido.
  if (!(await verifySha256Signature(env.GITHUB_WEBHOOK_SECRET, body, request.headers.get('X-Hub-Signature-256')))) {
    log('warn', { outcome: 'firma_invalida' })
    return json({ error: 'Firma inválida' }, 401)
  }

  const event = request.headers.get('X-GitHub-Event')
  const delivery = request.headers.get('X-GitHub-Delivery')
  if (!isValidDeliveryId(delivery)) return json({ error: 'Falta X-GitHub-Delivery' }, 400)
  if (event === 'ping') return json({ ok: true, event: 'ping' }, 200)
  if (event !== 'push') {
    log('info', { delivery, event, outcome: 'ignorado' })
    return json({ ignored: `evento ${event ?? 'desconocido'}` }, 202)
  }

  let payload: unknown
  try {
    payload = JSON.parse(new TextDecoder().decode(body))
  } catch {
    return json({ error: 'El cuerpo no es JSON' }, 400)
  }
  const decision = decidePush(payload)
  if ('ignore' in decision) {
    log('info', { delivery, outcome: 'ignorado', reason: decision.ignore })
    return json({ ignored: decision.ignore }, 202)
  }

  const deliveryKey = `delivery:${delivery}`
  if (await env.DELIVERIES.get(deliveryKey)) {
    log('info', { delivery, outcome: 'duplicado' })
    return json({ duplicate: true }, 200)
  }

  const response = await forwardToApi(env, delivery, decision.scan)
  if (!response) {
    log('error', { delivery, outcome: 'api_no_responde' })
    return json({ error: 'La API de Qubitor no respondió' }, 502)
  }
  if (!response.ok) {
    log('error', { delivery, outcome: 'api_error', status: response.status })
    return json({ error: 'La API de Qubitor rechazó el pedido' }, 502)
  }

  // Se marca recién cuando la API aceptó, así una entrega fallida se puede reenviar desde GitHub.
  await env.DELIVERIES.put(deliveryKey, '1', { expirationTtl: DELIVERY_TTL_SECONDS })
  const result = (await response.json().catch(() => ({}))) as Record<string, unknown>
  log('info', { delivery, outcome: 'escaneo_pedido', scans: Array.isArray(result.scans) ? result.scans.length : 0 })
  return json({ accepted: true, scans: result.scans ?? [], duplicate: result.duplicate ?? false }, 202)
}

async function forwardToApi(env: Env, delivery: string, push: PushToScan): Promise<Response | null> {
  const body = JSON.stringify({
    delivery_id: delivery,
    repository_url: push.repositoryUrl,
    commit_sha: push.commitSha,
    ref: push.ref,
  })
  const timestamp = Math.floor(Date.now() / 1000).toString()
  const signature = await signSha256(env.INTERNAL_WEBHOOK_SECRET, `${timestamp}.${body}`)
  try {
    return await fetch(`${env.QUBITOR_API_URL}/internal/github/push`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Qubitor-Timestamp': timestamp,
        'X-Qubitor-Signature': `sha256=${signature}`,
      },
      body,
      signal: AbortSignal.timeout(API_TIMEOUT_MS),
    })
  } catch {
    return null
  }
}

function json(data: unknown, status: number, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...headers },
  })
}

/** Logs estructurados en JSON (Workers Logs). Nunca incluyen secretos ni el cuerpo del evento. */
function log(level: 'info' | 'warn' | 'error', data: Record<string, unknown>): void {
  const line = JSON.stringify({ worker: 'qubitor-webhook', ...data })
  if (level === 'error') console.error(line)
  else if (level === 'warn') console.warn(line)
  else console.log(line)
}
