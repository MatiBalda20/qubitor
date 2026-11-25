import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/components/toast/ToastProvider'
import SecretsPage from './SecretsPage'

vi.mock('@/features/dashboard/dataSource', () => ({
  dashboardSource: {
    load: vi.fn().mockResolvedValue({
      repository: { id: 'repo_1', full_name: 'org/demo', provider: 'github', url: 'https://github.com/org/demo', default_branch: 'main', connected_at: '2026-11-01T00:00:00Z' },
      scan: { id: 'scan_1', repository_id: 'repo_1', status: 'completed', engines: ['secrets', 'sast'], progress: 100, stage: 'persist', commit_sha: 'abc1234', started_at: '2026-11-01T00:00:00Z', finished_at: '2026-11-01T00:01:00Z', risk_score: 80, grade: 'B', error: null },
      findings: [
        { id: 'f1', scan_id: 'scan_1', fingerprint: 'fp1', status: 'open', engine: 'secrets', rule_id: 'secrets.aws', title: 'AWS Access Key expuesta', severity: 'critical', file_path: '.env', line: 1, snippet: 'AWS_KEY=***', description: 'Rotar clave', cwe: 'CWE-798', cve: null, metadata: {}, triage: null },
        { id: 'f2', scan_id: 'scan_1', fingerprint: 'fp2', status: 'open', engine: 'sast', rule_id: 'sast.bandit.B307', title: 'Uso de eval()', severity: 'high', file_path: 'app.py', line: 2, snippet: 'eval(x)', description: 'Inseguro', cwe: 'CWE-78', cve: null, metadata: {}, triage: null },
      ],
    }),
    updateFinding: vi.fn(),
  },
}))

describe('SecretsPage', () => {
  it('muestra solo hallazgos del motor de secretos', async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <SecretsPage />
        </ToastProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText('AWS Access Key expuesta')).toBeInTheDocument()
    expect(screen.queryByText('Uso de eval()')).not.toBeInTheDocument()
  })
})