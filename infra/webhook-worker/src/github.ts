/** Validación del evento `push` de GitHub: solo se extrae lo que necesita Qubitor. */

const GITHUB_REPO_URL = /^https:\/\/github\.com\/(?!\.)[\w.-]{1,100}\/(?!\.)[\w.-]{1,100}$/
const COMMIT_SHA = /^[0-9a-f]{40}$/
const ZERO_SHA = '0'.repeat(40)
const DELIVERY_ID = /^[0-9A-Za-z-]{8,64}$/

export interface PushToScan {
  repositoryUrl: string
  commitSha: string
  ref: string
}

export type PushDecision = { scan: PushToScan } | { ignore: string }

export function isValidDeliveryId(id: string | null): id is string {
  return id !== null && DELIVERY_ID.test(id)
}

/** Decide si un push dispara un escaneo: solo los de la rama por defecto que dejan un commit. */
export function decidePush(payload: unknown): PushDecision {
  if (typeof payload !== 'object' || payload === null) return { ignore: 'payload inválido' }
  const event = payload as Record<string, unknown>
  const repository = event.repository as Record<string, unknown> | undefined
  const url = typeof repository?.html_url === 'string' ? repository.html_url : ''
  const defaultBranch = typeof repository?.default_branch === 'string' ? repository.default_branch : ''
  const ref = typeof event.ref === 'string' ? event.ref : ''
  const after = typeof event.after === 'string' ? event.after : ''

  if (!GITHUB_REPO_URL.test(url) || url.includes('..')) return { ignore: 'repositorio inválido' }
  if (event.deleted === true || after === ZERO_SHA) return { ignore: 'se borró la rama' }
  if (!COMMIT_SHA.test(after)) return { ignore: 'commit inválido' }
  if (!defaultBranch || ref !== `refs/heads/${defaultBranch}`) return { ignore: 'no es la rama por defecto' }
  return { scan: { repositoryUrl: url, commitSha: after, ref } }
}
