import { useId, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'
import { formatDateTime, formatNumber } from '@/lib/format'
import { GRADE_THRESHOLDS } from '@/lib/risk'
import type { HistoryScan } from './dataSource'

const HEIGHT = 220
const MARGIN = { top: 12, right: 44, bottom: 28, left: 40 }
// Cortes de la nota (sección 5 del plan): son la grilla del eje, así cada línea dice qué nota es.
const TICKS = GRADE_THRESHOLDS.filter((t) => t.min > 0).map((t) => ({ value: t.min, grade: t.grade }))

const shortDate = new Intl.DateTimeFormat('es-AR', { day: '2-digit', month: 'short' })

interface Point {
  scan: HistoryScan
  time: number
  score: number
  x: number
  y: number
}

/**
 * Evolución del Risk Score entre escaneos completados. Una sola serie, así que
 * no lleva leyenda: el título la nombra. Los hallazgos nuevos y resueltos van en
 * el tooltip y en la tabla, no en un segundo eje.
 */
export function RiskTrendChart({ scans }: { scans: readonly HistoryScan[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  const [active, setActive] = useState<number | null>(null)
  const titleId = useId()

  useLayoutEffect(() => {
    const element = containerRef.current
    if (!element) return
    // Se mide ya, sin esperar al primer aviso del observer: si el navegador no
    // está pintando (pestaña en segundo plano), ese aviso puede no llegar nunca.
    setWidth(element.clientWidth)
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const completed = useMemo(
    () =>
      scans
        .filter((s) => s.status === 'completed' && s.risk_score !== null)
        .map((s) => ({ scan: s, time: Date.parse(s.finished_at ?? s.started_at), score: s.risk_score! }))
        .sort((a, b) => a.time - b.time),
    [scans],
  )

  const points: Point[] = useMemo(() => {
    if (width === 0 || completed.length === 0) return []
    const plotWidth = width - MARGIN.left - MARGIN.right
    const first = completed[0].time
    const span = completed[completed.length - 1].time - first || 1
    return completed.map((c) => ({
      ...c,
      x: MARGIN.left + ((c.time - first) / span) * plotWidth,
      y: yFor(c.score),
    }))
  }, [completed, width])

  if (completed.length < 2) return null

  const last = points[points.length - 1]
  const shown = active !== null ? points[active] : null

  function nearest(event: PointerEvent<SVGSVGElement>) {
    const box = event.currentTarget.getBoundingClientRect()
    const x = event.clientX - box.left
    let best = 0
    points.forEach((p, i) => {
      if (Math.abs(p.x - x) < Math.abs(points[best].x - x)) best = i
    })
    setActive(best)
  }

  function onKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault()
      const step = event.key === 'ArrowRight' ? 1 : -1
      setActive((current) => Math.min(points.length - 1, Math.max(0, (current ?? points.length - 1) + step)))
    } else if (event.key === 'Escape') {
      setActive(null)
    }
  }

  return (
    <section aria-labelledby={titleId} className="rounded-sm bg-sheet shadow-sheet ring-1 ring-rule">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-5 py-3.5">
        <h2 id={titleId} className="text-base font-semibold text-ink">
          Evolución del Risk Score
        </h2>
        <p className="text-xs text-ink-3">Escaneos completados · las líneas marcan el corte de cada nota</p>
      </header>

      <div ref={containerRef} className="relative px-1 py-3 sm:px-3">
        {width > 0 && (
          <svg
            width={width}
            height={HEIGHT}
            role="img"
            tabIndex={0}
            aria-label={`Risk Score de ${completed.length} escaneos completados: pasó de ${formatNumber(completed[0].score)} a ${formatNumber(last.score)}. Usá las flechas para recorrer cada escaneo; el detalle completo está en la tabla.`}
            onPointerMove={nearest}
            onPointerLeave={() => setActive(null)}
            onBlur={() => setActive(null)}
            onKeyDown={onKeyDown}
            className="block touch-none outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-civic"
          >
            {/* Grilla recesiva: base 0 y los cortes de las notas. */}
            {[{ value: 0, grade: null }, ...TICKS, { value: 100, grade: null }].map((tick) => (
              <g key={tick.value}>
                <line
                  x1={MARGIN.left}
                  x2={width - MARGIN.right}
                  y1={yFor(tick.value)}
                  y2={yFor(tick.value)}
                  className="stroke-rule"
                  strokeWidth={1}
                />
                <text x={MARGIN.left - 8} y={yFor(tick.value)} dy="0.32em" textAnchor="end" className="fill-ink-3 text-[0.6875rem] tabular">
                  {tick.value}
                </text>
                {tick.grade && (
                  <text
                    x={width - MARGIN.right + 8}
                    y={yFor((tick.value + upperOf(tick.value)) / 2)}
                    dy="0.32em"
                    className="fill-ink-3 text-[0.6875rem] font-semibold"
                  >
                    {tick.grade}
                  </text>
                )}
              </g>
            ))}
            <text x={width - MARGIN.right + 8} y={yFor(20)} dy="0.32em" className="fill-ink-3 text-[0.6875rem] font-semibold">
              F
            </text>

            {/* Fechas del primer y último escaneo. */}
            {[points[0], last].map((p, i) => (
              <text
                key={i}
                x={p.x}
                y={HEIGHT - 8}
                textAnchor={i === 0 ? 'start' : 'end'}
                className="fill-ink-3 text-[0.6875rem] tabular"
              >
                {shortDate.format(p.time).replace('.', '')}
              </text>
            ))}

            {shown && (
              <line x1={shown.x} x2={shown.x} y1={MARGIN.top} y2={HEIGHT - MARGIN.bottom} className="stroke-ink-3" strokeWidth={1} />
            )}

            <polyline
              points={points.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              className="stroke-civic"
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {points.map((p, i) => (
              <circle
                key={p.scan.id}
                cx={p.x}
                cy={p.y}
                r={i === active ? 5.5 : 4}
                className="fill-civic stroke-sheet"
                strokeWidth={2}
              />
            ))}

            {/* Solo el último valor lleva etiqueta: el resto está en el tooltip y la tabla. */}
            <text x={last.x} y={last.y - 12} textAnchor="end" className="fill-ink text-xs font-semibold tabular">
              {formatNumber(last.score)}
            </text>
          </svg>
        )}

        {shown && <Tooltip point={shown} width={width} />}
      </div>
    </section>
  )
}

function Tooltip({ point, width }: { point: Point; width: number }) {
  const { scan } = point
  const left = Math.min(Math.max(point.x - 88, 4), width - 180)
  const above = point.y > HEIGHT / 2
  return (
    <div
      aria-live="polite"
      className="pointer-events-none absolute z-10 w-44 rounded-sm bg-sheet px-3 py-2 text-xs shadow-sheet ring-1 ring-rule"
      style={{ left, top: above ? point.y - 92 : point.y + 18 }}
    >
      <p className="flex items-baseline gap-1.5">
        <span className="font-display text-xl leading-none font-semibold text-ink tabular">{formatNumber(point.score)}</span>
        <span className="text-ink-2">Risk Score{scan.grade ? ` · nota ${scan.grade}` : ''}</span>
      </p>
      {scan.new_findings != null && scan.resolved_findings != null && (
        <p className="mt-1 text-ink-2 tabular">
          <strong className="font-semibold text-ink">+{scan.new_findings}</strong> nuevos ·{' '}
          <strong className="font-semibold text-ink">{scan.resolved_findings}</strong> resueltos
        </p>
      )}
      <p className="mt-1 text-ink-3 tabular">{formatDateTime(scan.finished_at ?? scan.started_at)}</p>
    </div>
  )
}

function yFor(score: number): number {
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  return MARGIN.top + (1 - score / 100) * plotHeight
}

/** Corte superior de la nota que empieza en `min` (100 para la A). */
function upperOf(min: number): number {
  const above = TICKS.map((t) => t.value).filter((v) => v > min)
  return above.length > 0 ? Math.min(...above) : 100
}
