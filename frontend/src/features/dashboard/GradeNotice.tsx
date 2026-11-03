import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { useRef } from 'react'
import { cn } from '@/lib/cn'
import { formatDateTime, formatDuration, formatNumber, formatStampDate } from '@/lib/format'
import { GRADE_THRESHOLDS } from '@/lib/risk'
import type { Grade, Scan } from '@/types/Scan'

gsap.registerPlugin(useGSAP)

const GRADE_COLOR: Record<Grade, { text: string; fill: string }> = {
  A: { text: 'text-ok', fill: 'bg-ok text-white' },
  B: { text: 'text-ok', fill: 'bg-ok text-white' },
  C: { text: 'text-sev-medium-ink', fill: 'bg-sev-medium text-ink' },
  D: { text: 'text-sev-high-ink', fill: 'bg-sev-high text-white' },
  F: { text: 'text-sev-critical', fill: 'bg-sev-critical text-white' },
}

interface GradeNoticeProps {
  score: number
  grade: Grade
  penalty: number
  counted: number
  total: number
  scan: Scan
  className?: string
}

/**
 * El cartel de la nota: como el certificado de inspección pegado en la
 * vidriera. El sello vuelve a estamparse cada vez que cambia la nota.
 */
export function GradeNotice({ score, grade, penalty, counted, total, scan, className }: GradeNoticeProps) {
  const root = useRef<HTMLElement>(null)
  const scoreRef = useRef<HTMLSpanElement>(null)
  const shown = useRef<{ score: number; grade: Grade } | null>(null)

  useGSAP(
    () => {
      const previous = shown.current
      shown.current = { score, grade }
      const scoreEl = scoreRef.current
      if (!scoreEl || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

      const counter = { value: previous?.score ?? 0 }
      const tl = gsap.timeline({ defaults: { ease: 'expo.out' } })

      if (!previous) {
        tl.from('[data-anim="letter"]', { autoAlpha: 0, scale: 0.9, filter: 'blur(6px)', duration: 0.9 }).from(
          '[data-anim="field"]',
          { autoAlpha: 0, y: 8, stagger: 0.06, duration: 0.6 },
          0.15,
        )
      }

      tl.to(
        counter,
        {
          value: score,
          duration: previous ? 0.8 : 1.3,
          ease: 'power3.out',
          onUpdate: () => {
            scoreEl.textContent = formatNumber(Math.round(counter.value * 2) / 2)
          },
        },
        0,
      )

      if (!previous || previous.grade !== grade) {
        tl.fromTo(
          '[data-anim="stamp"]',
          { autoAlpha: 0, scale: 1.8, rotate: -30 },
          { autoAlpha: 1, scale: 1, rotate: -12, duration: 0.42, ease: 'power4.in' },
          previous ? 0 : 0.75,
        ).to('[data-anim="stamp"]', { scale: 1.05, duration: 0.07, yoyo: true, repeat: 1, ease: 'power1.out' })
        if (previous) {
          tl.fromTo('[data-anim="letter"]', { scale: 0.94 }, { scale: 1, duration: 0.5 }, 0.42)
        }
      }

      // En StrictMode el efecto se monta dos veces: al desmontar se olvida lo mostrado.
      return () => {
        shown.current = null
      }
    },
    { scope: root, dependencies: [score, grade] },
  )

  const finishedAt = scan.finished_at ?? scan.started_at
  const colors = GRADE_COLOR[grade]

  return (
    <section
      ref={root}
      aria-labelledby="grade-notice-title"
      className={cn('relative overflow-hidden rounded-sm bg-sheet shadow-sheet ring-1 ring-civic/30', className)}
    >
      <header className="flex items-center justify-between gap-3 bg-civic px-5 py-2.5 text-civic-ink">
        <h2 id="grade-notice-title" className="font-display text-lg font-semibold tracking-[0.06em] uppercase">
          Resultado de la auditoría
        </h2>
        <span className="font-mono text-xs text-civic-muted">{scan.id}</span>
      </header>

      <div className="grid gap-6 p-5 sm:grid-cols-[auto_1fr] sm:gap-7">
        <div className="flex flex-col items-center gap-2 self-start">
          <div
            data-anim="letter"
            className="grid size-36 place-items-center rounded-xs border-[5px] border-double border-civic bg-sheet"
          >
            <span
              className={cn('font-display text-[7.5rem] leading-none font-bold', colors.text)}
              aria-label={`Nota ${grade}`}
            >
              {grade}
            </span>
          </div>
          <span className="field-label">Nota</span>
        </div>

        <dl className="grid content-start gap-4">
          <div data-anim="field">
            <dt className="field-label">Risk Score</dt>
            <dd className="mt-0.5 flex items-baseline gap-1.5">
              <span ref={scoreRef} className="font-display text-5xl leading-none font-semibold text-ink tabular">
                {formatNumber(score)}
              </span>
              <span className="text-sm text-ink-3">/ 100</span>
            </dd>
            <ScoreScale score={score} />
          </div>
          <div data-anim="field" className="grid grid-cols-2 gap-4">
            <div>
              <dt className="field-label">Penalización</dt>
              <dd className="mt-0.5 font-semibold text-ink tabular">{formatNumber(penalty)} pts</dd>
            </div>
            <div>
              <dt className="field-label">Penalizan</dt>
              <dd className="mt-0.5 font-semibold text-ink tabular">
                {counted} de {total}
              </dd>
            </div>
          </div>
          <div data-anim="field">
            <dt className="field-label">Escaneado</dt>
            <dd className="mt-0.5 text-sm text-ink-2 tabular">
              <span className="whitespace-nowrap">{formatDateTime(finishedAt)}</span>
              {scan.finished_at && (
                <span className="whitespace-nowrap"> · {formatDuration(scan.started_at, scan.finished_at)}</span>
              )}
            </dd>
          </div>
        </dl>
      </div>

      <GradeScale grade={grade} />

      <Stamp date={formatStampDate(finishedAt)} grade={grade} />
    </section>
  )
}

/** Regla 0–100 con los cortes de cada nota. */
function ScoreScale({ score }: { score: number }) {
  return (
    <div className="relative mt-3 h-2 rounded-full bg-civic-soft" aria-hidden="true">
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-civic transition-[width] duration-700 ease-(--ease-swift)"
        style={{ width: `${score}%` }}
      />
      {GRADE_THRESHOLDS.slice(0, -1).map(({ min }) => (
        <span key={min} className="absolute -inset-y-0.5 w-px bg-sheet" style={{ left: `${min}%` }} />
      ))}
    </div>
  )
}

/** Fila del formulario con todas las notas y sus cortes; la actual, marcada. */
function GradeScale({ grade }: { grade: Grade }) {
  return (
    <ol className="grid grid-cols-5 border-t border-rule" aria-label="Escala de notas">
      {GRADE_THRESHOLDS.map((t, index) => {
        const current = t.grade === grade
        return (
          <li
            key={t.grade}
            aria-current={current ? 'true' : undefined}
            className={cn(
              'flex items-baseline justify-center gap-1.5 py-2 transition-colors duration-300',
              index > 0 && 'border-l border-rule',
              current ? GRADE_COLOR[t.grade].fill : 'text-ink-3',
            )}
          >
            <span className="font-display text-lg leading-none font-bold">{t.grade}</span>
            <span className="text-[0.6875rem] tabular">{t.min === 0 ? '< 40' : `≥ ${t.min}`}</span>
          </li>
        )
      })}
    </ol>
  )
}

/** Sello circular con la fecha del escaneo. */
function Stamp({ date, grade }: { date: string; grade: Grade }) {
  return (
    <svg
      data-anim="stamp"
      viewBox="0 0 120 120"
      aria-hidden="true"
      className="pointer-events-none absolute top-14 right-3 size-28 -rotate-12 text-stamp opacity-90 mix-blend-multiply sm:right-5"
    >
      <defs>
        <path id="stamp-arc" d="M60,60 m-44,0 a44,44 0 1,1 88,0 a44,44 0 1,1 -88,0" />
      </defs>
      <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="60" cy="60" r="35" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <text fill="currentColor" fontSize="10.5" fontWeight="700" letterSpacing="2.4" fontFamily="'Barlow Condensed', sans-serif">
        <textPath href="#stamp-arc">QUBITOR · AUDITORÍA CONTINUA ·</textPath>
      </text>
      <text x="60" y="58" textAnchor="middle" fill="currentColor" fontSize="24" fontWeight="700" fontFamily="'Barlow Condensed', sans-serif">
        {grade}
      </text>
      <text x="60" y="74" textAnchor="middle" fill="currentColor" fontSize="9.5" fontWeight="600" letterSpacing="0.6" fontFamily="'Barlow Condensed', sans-serif">
        {date}
      </text>
    </svg>
  )
}
