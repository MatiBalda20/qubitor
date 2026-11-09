import { describe, expect, it } from 'vitest'
import { filterRepos, formatSize, isGitHubUrl, normalize, sortForConnect } from './search'
import type { GitHubRepo } from './types'

function repo(full_name: string, overrides: Partial<GitHubRepo> = {}): GitHubRepo {
  return {
    full_name,
    url: `https://github.com/${full_name}`,
    private: false,
    description: null,
    default_branch: 'main',
    size_bytes: 1024,
    updated_at: null,
    archived: false,
    connected: false,
    connectable: true,
    reason: null,
    ...overrides,
  }
}

const REPOS = [
  repo('acme/api-pagos', { description: 'Microservicio de pagos' }),
  repo('acme/landing', { description: 'Sitio institucional con configuración regional' }),
  repo('otra/api-usuarios'),
]

describe('búsqueda de repositorios', () => {
  it('sin texto devuelve todos', () => {
    expect(filterRepos(REPOS, '   ')).toHaveLength(3)
  })

  it('busca en el nombre y en la descripción, sin mayúsculas ni tildes', () => {
    expect(filterRepos(REPOS, 'API').map((r) => r.full_name)).toEqual(['acme/api-pagos', 'otra/api-usuarios'])
    expect(filterRepos(REPOS, 'configuracion').map((r) => r.full_name)).toEqual(['acme/landing'])
  })

  it('exige todas las palabras', () => {
    expect(filterRepos(REPOS, 'acme pagos').map((r) => r.full_name)).toEqual(['acme/api-pagos'])
  })

  it('normaliza tildes', () => {
    expect(normalize('  Configuración ')).toBe('configuracion')
  })
})

describe('orden para conectar', () => {
  it('primero los que se pueden conectar y al final los que no', () => {
    const sorted = sortForConnect([
      repo('a/no', { connectable: false, reason: 'privado' }),
      repo('a/ya', { connected: true }),
      repo('a/si'),
    ])

    expect(sorted.map((r) => r.full_name)).toEqual(['a/si', 'a/ya', 'a/no'])
  })
})

describe('validación de la URL', () => {
  it.each(['https://github.com/acme/demo', 'https://github.com/acme/demo.git', 'https://github.com/acme/demo/'])(
    'acepta %s',
    (url) => expect(isGitHubUrl(url)).toBe(true),
  )

  it.each([
    'http://github.com/acme/demo',
    'https://gitlab.com/acme/demo',
    'https://github.com/acme',
    'https://github.com/acme/../etc',
    'git@github.com:acme/demo.git',
    'https://usuario:clave@github.com/acme/demo',
  ])('rechaza %s', (url) => expect(isGitHubUrl(url)).toBe(false))
})

describe('tamaño', () => {
  it('en KB o MB', () => {
    expect(formatSize(180 * 1024)).toBe('180 KB')
    expect(formatSize(9.4 * 1024 * 1024)).toBe('9,4 MB')
  })
})
