import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/components/toast/ToastProvider'
import CodePage from './CodePage'

vi.mock('@/features/dashboard/dataSource', () => ({
  dashboardSource: {
    load: vi.fn().mockResolvedValue({
      repository: { id: 'repo_1', full_name: 'org/demo', provider: 'github', url: 'https://github.com/org/demo', default_branch: 'main', connected_at: '2026-11-01T00:00:00Z' },
      scan: { id: 'scan_1', repository_id: 'repo_1', status: 'completed', engines: ['sast', 'crypto', 'secrets'], progress: 100, stage: 'persist', commit_sha: 'abc1234', started_at: '2026-11-01T00:00:00Z', finished_at: '2026-11-01T00:01:00Z', risk_score: 80, grade: 'B', error: null },
      findings: [
        { id: 'f1', scan_id: 'scan_1', fingerprint: 'fp1', status: 'open', engine: 'sast', rule_id: 'sast.bandit.B307', title: 'Uso de eval()', severity: 'high', file_path: 'app.py', line: 2, snippet: 'eval(x)', description: 'Inseguro', cwe: 'CWE-78', cve: null, metadata: {}, triage: null },
        { id: 'f2', scan_id: 'scan_1', fingerprint: 'fp2', status: 'open', engine: 'crypto', rule_id: 'crypto.classic.weak-hash', title: 'Uso de MD5', severity: 'high', file_path: 'auth.py', line: 5, snippet: 'hashlib.md5(x)', description: 'Roto', cwe: 'CWE-327', cve: null, metadata: {}, triage: null },
        { id: 'f3', scan_id: 'scan_1', fingerprint: 'fp3', status: 'open', engine: 'crypto', rule_id: 'crypto.pqc.rsa-keygen', title: 'Clave RSA PQC', severity: 'medium', file_path: 'keys.py', line: 10, snippet: 'rsa.generate()', description: 'Shor', cwe: 'CWE-327', cve: null, metadata: {}, triage: null },
        { id: 'f4', scan_id: 'scan_1', fingerprint: 'fp4', status: 'open', engine: 'secrets', rule_id: 'secrets.aws', title: 'AWS Access Key expuesta', severity: 'critical', file_path: '.env', line: 1, snippet: 'AWS_KEY=***', description: 'Rotar', cwe: 'CWE-798', cve: null, metadata: {}, triage: null },
      ],
    }),
    updateFinding: vi.fn(),
  },
}))

describe('CodePage', () => {
  it('muestra SAST y criptografía clásica, excluyendo PQC y secretos', async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <CodePage />
        </ToastProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Uso de eval()')).toBeInTheDocument()
    expect(screen.getByText('Uso de MD5')).toBeInTheDocument()
    expect(screen.queryByText('Clave RSA PQC')).not.toBeInTheDocument()
    expect(screen.queryByText('AWS Access Key expuesta')).not.toBeInTheDocument()
  })
})