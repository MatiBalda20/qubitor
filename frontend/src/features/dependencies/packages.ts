import { effectiveSeverity } from '@/lib/risk'
import type { FindingRecord, Severity } from '@/types/Finding'

/**
 * Agrupa los hallazgos del motor SCA por paquete. Un paquete puede tener
 * varias vulnerabilidades, cada una corregida en una versión distinta: para
 * resolverlas todas hay que actualizar a la más alta.
 */

/** Una vulnerabilidad de un paquete, con los datos que el motor deja en metadata. */
export interface Vulnerability {
  finding: FindingRecord
  /** CVE si lo tiene; si no, el id de OSV (GHSA-…, PYSEC-…). */
  id: string
  url: string
  summary: string
  severity: Severity
  cvss: number | null
  fixedVersion: string | null
  /** Abierta y no descartada: hay que corregirla. */
  pending: boolean
}

export interface PackageGroup {
  key: string
  name: string
  ecosystem: string
  installedVersion: string
  /** Manifiesto donde se declara, con su línea. */
  location: string
  vulnerabilities: Vulnerability[]
  pendingCount: number
  /** Peor severidad entre las pendientes; null si no queda ninguna. */
  worstSeverity: Severity | null
  maxCvss: number | null
  /** Versión que corrige todas las pendientes que tienen arreglo. */
  targetVersion: string | null
  /** Pendientes que todavía no tienen versión corregida. */
  unfixedCount: number
  command: string | null
}

const SEVERITY_RANK: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }

export function groupByPackage(findings: readonly FindingRecord[]): PackageGroup[] {
  const groups = new Map<string, Vulnerability[]>()
  for (const finding of findings) {
    if (finding.engine !== 'sca') continue
    const key = `${text(finding.metadata, 'ecosystem')}|${text(finding.metadata, 'package')}|${finding.file_path}`
    groups.set(key, [...(groups.get(key) ?? []), toVulnerability(finding)])
  }
  return [...groups.entries()].map(([key, vulnerabilities]) => toGroup(key, vulnerabilities)).sort(compareGroups)
}

/** Comandos para actualizar todos los paquetes pendientes, uno por ecosistema. */
export function combinedCommands(groups: readonly PackageGroup[]): string[] {
  const byEcosystem = new Map<string, string[]>()
  for (const group of groups) {
    if (group.pendingCount === 0 || group.targetVersion === null) continue
    byEcosystem.set(group.ecosystem, [...(byEcosystem.get(group.ecosystem) ?? []), pinned(group)])
  }
  return [...byEcosystem.entries()].map(([ecosystem, packages]) => `${installer(ecosystem)} ${packages.join(' ')}`)
}

/** Compara versiones como números ("4.17.21" > "4.17.5"), ignorando sufijos de pre-release. */
export function compareVersions(a: string, b: string): number {
  const left = versionParts(a)
  const right = versionParts(b)
  for (let i = 0; i < Math.max(left.length, right.length); i++) {
    const diff = (left[i] ?? 0) - (right[i] ?? 0)
    if (diff !== 0) return diff
  }
  return 0
}

function toVulnerability(finding: FindingRecord): Vulnerability {
  const vulnId = text(finding.metadata, 'vuln_id') || finding.rule_id
  const prefix = `${text(finding.metadata, 'package')} ${text(finding.metadata, 'installed_version')}: `
  return {
    finding,
    id: finding.cve ?? vulnId,
    url: finding.cve
      ? `https://nvd.nist.gov/vuln/detail/${finding.cve}`
      : `https://osv.dev/vulnerability/${encodeURIComponent(vulnId)}`,
    summary: finding.title.startsWith(prefix) ? finding.title.slice(prefix.length) : finding.title,
    severity: effectiveSeverity(finding),
    cvss: number(finding.metadata, 'cvss'),
    fixedVersion: text(finding.metadata, 'fixed_version') || null,
    pending: finding.status === 'open' && !finding.triage?.is_false_positive,
  }
}

function toGroup(key: string, vulnerabilities: Vulnerability[]): PackageGroup {
  const [first] = vulnerabilities
  const pending = vulnerabilities.filter((v) => v.pending)
  const fixes = pending.flatMap((v) => (v.fixedVersion ? [v.fixedVersion] : []))
  const targetVersion = fixes.length > 0 ? fixes.reduce((max, v) => (compareVersions(v, max) > 0 ? v : max)) : null
  const scores = pending.flatMap((v) => (v.cvss === null ? [] : [v.cvss]))

  const group: PackageGroup = {
    key,
    name: text(first.finding.metadata, 'package'),
    ecosystem: text(first.finding.metadata, 'ecosystem'),
    installedVersion: text(first.finding.metadata, 'installed_version'),
    location: first.finding.line != null ? `${first.finding.file_path}:${first.finding.line}` : first.finding.file_path,
    vulnerabilities: [...vulnerabilities].sort(compareVulnerabilities),
    pendingCount: pending.length,
    worstSeverity: pending.reduce<Severity | null>(
      (worst, v) => (worst === null || SEVERITY_RANK[v.severity] < SEVERITY_RANK[worst] ? v.severity : worst),
      null,
    ),
    maxCvss: scores.length > 0 ? Math.max(...scores) : null,
    targetVersion,
    unfixedCount: pending.filter((v) => v.fixedVersion === null).length,
    command: null,
  }
  group.command = targetVersion && pending.length > 0 ? `${installer(group.ecosystem)} ${pinned(group)}` : null
  return group
}

function compareVulnerabilities(a: Vulnerability, b: Vulnerability): number {
  return (
    Number(b.pending) - Number(a.pending) ||
    SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] ||
    (b.cvss ?? -1) - (a.cvss ?? -1) ||
    a.id.localeCompare(b.id)
  )
}

function compareGroups(a: PackageGroup, b: PackageGroup): number {
  const rank = (g: PackageGroup) => (g.worstSeverity === null ? 5 : SEVERITY_RANK[g.worstSeverity])
  return rank(a) - rank(b) || (b.maxCvss ?? -1) - (a.maxCvss ?? -1) || a.name.localeCompare(b.name)
}

function installer(ecosystem: string): string {
  return ecosystem === 'PyPI' ? 'pip install' : 'npm install'
}

function pinned(group: PackageGroup): string {
  return group.ecosystem === 'PyPI' ? `${group.name}==${group.targetVersion}` : `${group.name}@${group.targetVersion}`
}

function versionParts(version: string): number[] {
  const release = version.split(/[-+]/, 1)[0]
  return (release.match(/\d+/g) ?? []).map(Number)
}

function text(metadata: Record<string, unknown>, key: string): string {
  const value = metadata[key]
  return typeof value === 'string' ? value : ''
}

function number(metadata: Record<string, unknown>, key: string): number | null {
  const value = metadata[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}
