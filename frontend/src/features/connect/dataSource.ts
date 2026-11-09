import { api, request } from '@/lib/api'
import { USE_MOCKS } from '@/lib/config'
import type { Repository, Scan } from '@/types/Scan'
import mock from './mock.json'
import type { GitHubRepoPage } from './types'

/** De dónde saca la pantalla «Conectar repositorio» sus datos: la API real o los mocks. */
export interface ConnectSource {
  listGitHubRepos: (page: number) => Promise<GitHubRepoPage>
  /** Conecta un repo de la cuenta de GitHub del usuario (lo valida el backend contra GitHub). */
  connectGitHubRepo: (fullName: string) => Promise<Repository>
  /** Conecta un repo público pegando su URL. */
  connectPublicUrl: (url: string) => Promise<Repository>
  startScan: (repositoryId: string) => Promise<Scan>
  getScan: (scanId: string) => Promise<Scan>
}

export const PER_PAGE = 30

const apiSource: ConnectSource = {
  listGitHubRepos: (page) => request<GitHubRepoPage>(`/github/repositories?page=${page}&per_page=${PER_PAGE}`),
  connectGitHubRepo: (fullName) =>
    request<Repository>('/github/repositories', { method: 'POST', body: JSON.stringify({ full_name: fullName }) }),
  connectPublicUrl: api.connectRepository,
  startScan: api.startScan,
  getScan: api.getScan,
}

/* ---------- Mocks: mismo formato que la API ---------- */

const MOCK_LATENCY_MS = 350
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const mockRepository = (url: string): Repository => ({
  id: `repo_${url.split('/').pop()}`,
  provider: 'github',
  full_name: url.replace('https://github.com/', ''),
  url,
  default_branch: 'main',
  connected_at: new Date().toISOString(),
})

const mockScan = (repositoryId: string, status: Scan['status']): Scan => ({
  id: `scan_${repositoryId}`,
  repository_id: repositoryId,
  status,
  engines: ['sast', 'sca', 'secrets', 'crypto'],
  progress: status === 'completed' ? 100 : null,
  stage: null,
  commit_sha: status === 'completed' ? 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4' : null,
  started_at: new Date().toISOString(),
  finished_at: status === 'completed' ? new Date().toISOString() : null,
  risk_score: status === 'completed' ? 72 : null,
  grade: status === 'completed' ? 'C' : null,
  error: null,
})

const mockSource: ConnectSource = {
  async listGitHubRepos(page) {
    await wait(MOCK_LATENCY_MS)
    const found = mock.pages.find((p) => p.page === page) ?? { items: [], page, has_next: false }
    return structuredClone(found) as GitHubRepoPage
  },
  async connectGitHubRepo(fullName) {
    await wait(MOCK_LATENCY_MS)
    return mockRepository(`https://github.com/${fullName}`)
  },
  async connectPublicUrl(url) {
    await wait(MOCK_LATENCY_MS)
    return mockRepository(url.replace(/\.git$/, '').replace(/\/$/, ''))
  },
  async startScan(repositoryId) {
    await wait(MOCK_LATENCY_MS / 2)
    return mockScan(repositoryId, 'queued')
  },
  async getScan(scanId) {
    await wait(MOCK_LATENCY_MS)
    return mockScan(scanId.replace(/^scan_/, ''), 'completed')
  },
}

export const connectSource: ConnectSource = USE_MOCKS ? mockSource : apiSource
