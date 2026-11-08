const numberFormat = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 1 })

const dateTimeFormat = new Intl.DateTimeFormat('es-AR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const stampDateFormat = new Intl.DateTimeFormat('es-AR', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

export function formatNumber(value: number): string {
  return numberFormat.format(value)
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}

/** Fecha corta en mayúsculas para el sello del cartel: "03 NOV 2026". */
export function formatStampDate(iso: string): string {
  return stampDateFormat.format(new Date(iso)).replace(/\./g, '').replace(/ de /g, ' ').toUpperCase()
}

/** Duración legible entre dos fechas: "1 min 12 s". */
export function formatDuration(fromIso: string, toIso: string): string {
  const seconds = Math.max(0, Math.round((Date.parse(toIso) - Date.parse(fromIso)) / 1000))
  const minutes = Math.floor(seconds / 60)
  return minutes > 0 ? `${minutes} min ${seconds % 60} s` : `${seconds} s`
}

export function pluralize(count: number, singular: string, plural: string): string {
  return `${formatNumber(count)} ${count === 1 ? singular : plural}`
}
