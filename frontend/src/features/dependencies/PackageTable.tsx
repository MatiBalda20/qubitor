import { Check, ChevronDown, Copy, ExternalLink } from 'lucide-react'
import { useId, useState } from 'react'
import { SeverityBadge } from '@/components/SeverityBadge'
import { StatusStamp } from '@/components/StatusStamp'
import { cn } from '@/lib/cn'
import { formatNumber, pluralize } from '@/lib/format'
import type { PackageGroup, Vulnerability } from './packages'

interface PackageTableProps {
  groups: readonly PackageGroup[]
  onCopy: (command: string) => void
}

const COLUMNS = 'md:grid-cols-[minmax(0,1fr)_6.5rem_7.5rem_9.5rem_4.5rem_1.25rem]'

/** Paquetes vulnerables, cada uno con sus vulnerabilidades en un acordeón. */
export function PackageTable({ groups, onCopy }: PackageTableProps) {
  const [openKey, setOpenKey] = useState<string | null>(null)

  return (
    <section aria-labelledby="packages-title" className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id="packages-title" className="text-base font-semibold text-ink">
          Paquetes vulnerables
        </h2>
        <p className="text-xs text-ink-3">Ordenados por la peor vulnerabilidad pendiente</p>
      </header>

      <div aria-hidden="true" className={cn('hidden gap-4 border-b border-rule bg-paper/60 py-2 pr-16 pl-5 md:grid', COLUMNS)}>
        {['Paquete', 'Instalada', 'Actualizar a', 'Vulnerabilidades', 'CVSS máx.', ''].map((label) => (
          <span key={label} className="field-label">
            {label}
          </span>
        ))}
      </div>

      <ul className="divide-y divide-rule">
        {groups.map((group) => (
          <PackageRow
            key={group.key}
            group={group}
            open={openKey === group.key}
            onToggle={() => setOpenKey((current) => (current === group.key ? null : group.key))}
            onCopy={onCopy}
          />
        ))}
      </ul>
    </section>
  )
}

interface PackageRowProps {
  group: PackageGroup
  open: boolean
  onToggle: () => void
  onCopy: (command: string) => void
}

function PackageRow({ group, open, onToggle, onCopy }: PackageRowProps) {
  const panelId = useId()
  const resolved = group.pendingCount === 0

  return (
    <li className="t-acc" data-open={open}>
      <div className={cn('flex items-center transition-colors duration-150 hover:bg-civic-soft/50', open && 'bg-civic-soft/50')}>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={onToggle}
          className={cn(
            'grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 py-3.5 pl-4 text-left sm:pl-5',
            COLUMNS,
          )}
        >
          <span className="min-w-0">
            <span className={cn('block font-mono text-[0.9375rem] font-medium text-ink', resolved && 'text-ink-3 line-through')}>
              {group.name}
            </span>
            <span className="mt-0.5 block truncate text-xs text-ink-3">
              {group.ecosystem} · <span className="font-mono">{group.location}</span>
            </span>
          </span>
          <span className="t-acc-chevron col-start-2 row-start-1 justify-self-end text-ink-3 md:col-start-6">
            <ChevronDown className="size-5" strokeWidth={1.75} aria-hidden="true" />
          </span>
          <span className="col-span-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm md:contents">
            <span className="font-mono text-[0.8125rem] text-ink-2 md:row-start-1 md:col-start-2">
              <span className="font-sans text-ink-3 md:hidden">instalada </span>
              {group.installedVersion}
            </span>
            <span className="font-mono text-[0.8125rem] font-semibold text-ink md:row-start-1 md:col-start-3">
              <span className="font-sans font-normal text-ink-3 md:hidden">→ </span>
              {group.targetVersion ?? <span className="font-sans font-normal text-ink-3">Sin arreglo</span>}
            </span>
            <span className="flex items-center gap-2 md:row-start-1 md:col-start-4">
              {group.worstSeverity && <SeverityBadge severity={group.worstSeverity} size="sm" />}
              <span className="text-ink-2 tabular">
                {resolved ? 'Sin pendientes' : pluralize(group.pendingCount, 'pendiente', 'pendientes')}
              </span>
            </span>
            <span className="font-display text-lg leading-none font-semibold text-ink tabular md:row-start-1 md:col-start-5">
              <span className="font-sans text-xs font-normal text-ink-3 md:hidden">CVSS </span>
              {group.maxCvss === null ? '—' : formatNumber(group.maxCvss)}
            </span>
          </span>
        </button>
        <div className="px-3 sm:px-4">
          {group.command && <CopyButton label={`Copiar el comando para actualizar ${group.name}`} onClick={() => onCopy(group.command!)} />}
        </div>
      </div>

      <div id={panelId} className="t-acc-panel" inert={!open}>
        <div className="t-acc-panel-inner">
          <div className="space-y-4 border-t border-rule bg-paper/40 px-4 py-5 sm:px-5">
            {group.command && (
              <div>
                <p className="field-label mb-1.5">Comando de actualización</p>
                <div className="flex items-center gap-2 rounded-sm bg-sheet py-1.5 pr-1.5 pl-3 ring-1 ring-rule ring-inset">
                  <code className="min-w-0 flex-1 truncate font-mono text-[0.8125rem] text-ink">{group.command}</code>
                  <CopyButton label={`Copiar el comando para actualizar ${group.name}`} onClick={() => onCopy(group.command!)} />
                </div>
                {group.unfixedCount > 0 && (
                  <p className="mt-1.5 text-xs text-ink-2">
                    {pluralize(group.unfixedCount, 'vulnerabilidad todavía no tiene', 'vulnerabilidades todavía no tienen')}{' '}
                    versión corregida: este comando no las resuelve.
                  </p>
                )}
              </div>
            )}
            <ul className="divide-y divide-rule rounded-sm bg-sheet ring-1 ring-rule">
              {group.vulnerabilities.map((vulnerability) => (
                <VulnerabilityItem key={vulnerability.finding.id} vulnerability={vulnerability} />
              ))}
            </ul>
          </div>
        </div>
      </div>
    </li>
  )
}

function VulnerabilityItem({ vulnerability }: { vulnerability: Vulnerability }) {
  const { finding, pending } = vulnerability
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-4 gap-y-1.5 px-4 py-3 sm:grid-cols-[6rem_minmax(0,1fr)_5rem_7rem]">
      <span className={cn(!pending && 'opacity-55')}>
        <SeverityBadge severity={vulnerability.severity} size="sm" />
      </span>
      <span className="col-span-2 row-start-2 min-w-0 sm:col-span-1 sm:row-start-auto">
        <a
          href={vulnerability.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-[0.8125rem] font-medium text-civic underline decoration-civic/30 hover:decoration-civic"
        >
          {vulnerability.id}
          <ExternalLink className="size-3.5" strokeWidth={1.75} aria-hidden="true" />
          <span className="sr-only">(se abre en otra pestaña)</span>
        </a>
        <span className={cn('mt-0.5 block text-sm text-ink-2', !pending && 'text-ink-3 line-through decoration-ink-3/60')}>
          {vulnerability.summary}
        </span>
        {!pending && <StatusStamp status={finding.status === 'open' ? 'false_positive' : finding.status} className="mt-1.5" />}
      </span>
      <span className="col-start-2 row-start-1 text-right text-sm sm:col-start-auto sm:row-start-auto">
        <span className="field-label block">CVSS</span>
        <span className="font-semibold text-ink tabular">{vulnerability.cvss === null ? '—' : formatNumber(vulnerability.cvss)}</span>
      </span>
      <span className="hidden text-right text-sm sm:block">
        <span className="field-label block">Corregida en</span>
        <span className="font-mono text-[0.8125rem] text-ink">{vulnerability.fixedVersion ?? '—'}</span>
      </span>
    </li>
  )
}

function CopyButton({ label, onClick }: { label: string; onClick: () => void }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        onClick()
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1500)
      }}
      aria-label={label}
      title={label}
      className="grid size-9 shrink-0 place-items-center rounded-sm bg-sheet text-ink-2 ring-1 ring-rule-2 ring-inset transition-[background-color,color,scale] duration-150 hover:bg-civic-soft hover:text-ink active:scale-[0.96]"
    >
      {copied ? <Check className="size-4" strokeWidth={2} aria-hidden="true" /> : <Copy className="size-4" strokeWidth={2} aria-hidden="true" />}
    </button>
  )
}
