import type { Severity } from '@/types/Finding'

/** Clases de color por severidad, compartidas por badges, barras y leyendas. */
export const SEVERITY_STYLES: Record<Severity, { badge: string; bar: string; text: string }> = {
  critical: {
    badge: 'bg-sev-critical text-white ring-sev-critical',
    bar: 'bg-sev-critical',
    text: 'text-sev-critical',
  },
  high: {
    badge: 'bg-sev-high-soft text-sev-high-ink ring-sev-high/45',
    bar: 'bg-sev-high',
    text: 'text-sev-high-ink',
  },
  medium: {
    badge: 'bg-sev-medium-soft text-sev-medium-ink ring-sev-medium/60',
    bar: 'bg-sev-medium',
    text: 'text-sev-medium-ink',
  },
  low: {
    badge: 'bg-sev-low-soft text-sev-low-ink ring-sev-low/40',
    bar: 'bg-sev-low',
    text: 'text-sev-low-ink',
  },
  info: {
    badge: 'bg-sev-info-soft text-sev-info-ink ring-sev-info/50',
    bar: 'bg-sev-info',
    text: 'text-sev-info-ink',
  },
}
