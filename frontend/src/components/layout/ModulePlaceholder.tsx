import { Hammer } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from './PageHeader'

interface ModulePlaceholderProps {
  title: string
  owner: string
  folder: string
}

/**
 * Vista de un módulo que todavía no se construyó. Cada integrante la
 * reemplaza en App.tsx por su página de features/<módulo>/.
 */
export function ModulePlaceholder({ title, owner, folder }: ModulePlaceholderProps) {
  return (
    <>
      <PageHeader title={title} />
      <div className="px-4 pb-10 sm:px-8">
        <div className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
          <EmptyState
            icon={Hammer}
            title="Vista en construcción"
            description={
              <>
                La construye el {owner} en <code className="font-mono text-[0.8125rem]">{folder}</code>. Mientras
                tanto, los hallazgos están en el dashboard general.
              </>
            }
            action={
              <Link to="/" className="text-sm font-semibold text-civic underline decoration-civic/30 hover:decoration-civic">
                Volver al dashboard
              </Link>
            }
          />
        </div>
      </div>
    </>
  )
}
