import { cn } from '@/lib/cn'

interface CodeSnippetProps {
  /** Fragmento tal como lo devuelve el motor (máx. 5 líneas, secretos enmascarados). */
  code: string
  /** Línea del archivo donde está el hallazgo; se resalta. */
  line?: number | null
  /** Primera línea del fragmento. Si falta, se asume que el hallazgo está en el centro. */
  startLine?: number
  filePath?: string
  className?: string
}

/** Fragmento de código con números de línea y la línea del hallazgo resaltada. */
export function CodeSnippet({ code, line, startLine, filePath, className }: CodeSnippetProps) {
  const lines = code.replace(/\s+$/, '').split('\n')
  const first = startLine ?? (line != null ? Math.max(1, line - Math.floor(lines.length / 2)) : 1)

  return (
    <figure className={cn('overflow-hidden rounded-sm bg-[oklch(0.21_0.03_262)] ring-1 ring-ink/10', className)}>
      {filePath && (
        <figcaption className="border-b border-white/10 px-3.5 py-2 font-mono text-[0.75rem] text-[oklch(0.8_0.02_262)]">
          {filePath}
          {line != null && <span className="text-[oklch(0.65_0.02_262)]">:{line}</span>}
        </figcaption>
      )}
      <pre className="overflow-x-auto py-2.5 font-mono text-[0.8125rem] leading-6">
        <code className="block min-w-max">
          {lines.map((text, index) => {
            const number = first + index
            const highlighted = line != null && number === line
            return (
              <span
                key={number}
                className={cn(
                  'grid grid-cols-[3.25rem_1fr] pr-4',
                  highlighted ? 'bg-sev-medium/15 text-white' : 'text-[oklch(0.86_0.015_262)]',
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    'select-none border-r pr-3 text-right tabular',
                    highlighted ? 'border-sev-medium text-sev-medium' : 'border-transparent text-[oklch(0.55_0.02_262)]',
                  )}
                >
                  {number}
                </span>
                <span className="pl-3.5 whitespace-pre">{text || ' '}</span>
              </span>
            )
          })}
        </code>
      </pre>
    </figure>
  )
}
