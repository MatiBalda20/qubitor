import type { GitHubRepo } from './types'

/** Sin mayúsculas ni tildes, para que «configuracion» encuentre «Configuración». */
export function normalize(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

/** Repos cuyo nombre o descripción contienen todas las palabras buscadas. */
export function filterRepos(repos: readonly GitHubRepo[], query: string): GitHubRepo[] {
  const words = normalize(query).split(/\s+/).filter(Boolean)
  if (words.length === 0) return [...repos]
  return repos.filter((repo) => {
    const haystack = normalize(`${repo.full_name} ${repo.description ?? ''}`)
    return words.every((word) => haystack.includes(word))
  })
}

/** Primero los que se pueden conectar, después los ya conectados y al final los que no se pueden. */
export function sortForConnect(repos: readonly GitHubRepo[]): GitHubRepo[] {
  const rank = (repo: GitHubRepo) => (repo.connected ? 1 : repo.connectable ? 0 : 2)
  return [...repos].sort((a, b) => rank(a) - rank(b))
}

const GITHUB_URL = /^https:\/\/github\.com\/(?!\.)[\w.-]+\/(?!\.)[\w.-]+?(\.git)?\/?$/

/** Misma validación que el backend (app/worker/clone.py), para avisar antes de enviar. */
export function isGitHubUrl(url: string): boolean {
  return GITHUB_URL.test(url.trim()) && !url.includes('..')
}

export function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toLocaleString('es-AR', { maximumFractionDigits: 1 })} MB`
}
