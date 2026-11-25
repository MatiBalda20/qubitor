import { KeyRound } from 'lucide-react'
import type { FindingRecord } from '@/types/Finding'

interface ProviderGuide {
  id: string
  name: string
  steps: string[]
}

const GUIDES: Record<string, ProviderGuide> = {
  aws: {
    id: 'aws',
    name: 'AWS Access Key',
    steps: [
      'Ingresá a AWS IAM > Users > Security credentials y desactivá o eliminá la Access Key comprometida.',
      'Generá una nueva clave y cargala como variable de entorno en tu servicio (nunca en el código).',
      'Revisá AWS CloudTrail para confirmar que no hubo actividad no autorizada.',
    ],
  },
  github: {
    id: 'github',
    name: 'GitHub Token',
    steps: [
      'Andá a GitHub > Settings > Developer settings > Personal access tokens y revocá el token expuesto.',
      'Creá uno nuevo con los permisos mínimos necesarios y guardalo en los secrets del entorno.',
      'Revisá el Audit Log de tu cuenta u organización por accesos inesperados.',
    ],
  },
  google: {
    id: 'google',
    name: 'Google API Key',
    steps: [
      'Abrí Google Cloud Console > APIs & Services > Credentials y eliminá o regenerá la API Key.',
      'Aplicá restricciones por IP, dominio o API específica sobre la nueva clave.',
    ],
  },
  slack: {
    id: 'slack',
    name: 'Slack Token',
    steps: [
      'Ingresá a api.slack.com/apps, seleccioná la app y revocá el token en OAuth & Permissions.',
      'Reinstalá la app en el workspace para emitir un token nuevo y guardalo en variables de entorno.',
    ],
  },
  private_key: {
    id: 'private_key',
    name: 'Clave privada',
    steps: [
      'Revocá el certificado o quitá la clave pública de los servidores (por ejemplo, ~/.ssh/authorized_keys o GitHub).',
      'Generá un par de claves nuevo y excluí archivos *.pem y *.key en .gitignore.',
    ],
  },
  generic: {
    id: 'generic',
    name: 'Credencial genérica',
    steps: [
      'Rotá la contraseña o token directamente en el servicio proveedor.',
      'Mové el valor a un archivo .env ignorado por Git o al gestor de secretos de tu plataforma cloud.',
    ],
  },
}

function detectProviders(findings: readonly FindingRecord[]): ProviderGuide[] {
  const keys = new Set<string>()
  for (const f of findings) {
    const rule = f.rule_id.toLowerCase()
    if (rule.includes('aws')) keys.add('aws')
    else if (rule.includes('github')) keys.add('github')
    else if (rule.includes('google')) keys.add('google')
    else if (rule.includes('slack')) keys.add('slack')
    else if (rule.includes('private_key') || rule.includes('private-key')) keys.add('private_key')
    else keys.add('generic')
  }
  return [...keys].map((k) => GUIDES[k])
}

export function RotationGuide({ findings }: { findings: readonly FindingRecord[] }) {
  const guides = detectProviders(findings)
  if (guides.length === 0) return null

  return (
    <section aria-labelledby="rotation-guide-title" className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
      <header className="flex items-center gap-2 border-b border-rule px-5 py-3.5">
        <KeyRound className="size-4 text-civic" strokeWidth={1.75} aria-hidden="true" />
        <h2 id="rotation-guide-title" className="text-base font-semibold text-ink">
          Guía de rotación por proveedor
        </h2>
      </header>
      <div className="divide-y divide-rule">
        {guides.map((guide) => (
          <div key={guide.id} className="px-5 py-4">
            <h3 className="text-sm font-semibold text-ink">{guide.name}</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-ink-2">
              {guide.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </section>
  )
}