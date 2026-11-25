import { FileDiff } from 'lucide-react'
import type { FindingRecord } from '@/types/Finding'

interface PatchProposal {
  id: string
  file: string
  title: string
  before: string
  after: string
}

const PATCH_TEMPLATES: Record<string, { before: string; after: string }> = {
  'crypto.classic.weak-hash': {
    before: '- hashlib.md5(data).hexdigest()',
    after: '+ hashlib.sha256(data).hexdigest()  # o Argon2id para contraseñas',
  },
  'crypto.classic.aes-ecb': {
    before: '- Cipher(algorithms.AES(key), modes.ECB())',
    after: '+ Cipher(algorithms.AES(key), modes.GCM(iv))',
  },
  'crypto.classic.rsa-weak-key': {
    before: '- rsa.generate_private_key(public_exponent=65537, key_size=1024)',
    after: '+ rsa.generate_private_key(public_exponent=65537, key_size=3072)',
  },
  'crypto.classic.insecure-random': {
    before: '- token = "".join(random.choice(ALFABETO) for _ in range(32))',
    after: '+ token = secrets.token_urlsafe(32)',
  },
  'crypto.classic.tls-insecure': {
    before: '- requests.get(url, verify=False)',
    after: '+ requests.get(url, verify=True)',
  },
  'crypto.classic.weak-cipher': {
    before: '- DES.new(key, DES.MODE_ECB)',
    after: '+ AES.new(key_32_bytes, AES.MODE_GCM)',
  },
}

function buildPatches(findings: readonly FindingRecord[]): PatchProposal[] {
  const proposals: PatchProposal[] = []
  for (const f of findings) {
    if (f.status !== 'open') continue
    const template =
      PATCH_TEMPLATES[f.rule_id] ??
      (f.rule_id.startsWith('crypto.classic.weak-hash') ? PATCH_TEMPLATES['crypto.classic.weak-hash'] : undefined)
    if (!template) continue
    proposals.push({
      id: f.id,
      file: f.line != null ? `${f.file_path}:${f.line}` : f.file_path,
      title: f.title,
      before: template.before,
      after: template.after,
    })
  }
  return proposals
}

export function SuggestedPatches({ findings }: { findings: readonly FindingRecord[] }) {
  const patches = buildPatches(findings)
  if (patches.length === 0) return null

  return (
    <section aria-labelledby="suggested-patches-title" className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <div className="flex items-center gap-2">
          <FileDiff className="size-4 text-civic" strokeWidth={1.75} aria-hidden="true" />
          <h2 id="suggested-patches-title" className="text-base font-semibold text-ink">
            Parches sugeridos
          </h2>
        </div>
        <p className="text-xs text-ink-3">Correcciones mecánicas para criptografía clásica</p>
      </header>
      <div className="divide-y divide-rule">
        {patches.map((patch) => (
          <div key={patch.id} className="space-y-2 px-5 py-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{patch.title}</h3>
              <span className="font-mono text-xs text-ink-3">{patch.file}</span>
            </div>
            <pre className="overflow-x-auto rounded-sm bg-[oklch(0.21_0.03_262)] p-3 font-mono text-[0.8125rem] leading-6">
              <code className="block min-w-max">
                <span className="block bg-sev-critical/20 px-2 text-red-200">{patch.before}</span>
                <span className="block bg-ok/20 px-2 text-emerald-200">{patch.after}</span>
              </code>
            </pre>
          </div>
        ))}
      </div>
    </section>
  )
}