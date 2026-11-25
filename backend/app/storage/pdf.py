"""Reporte del escaneo en PDF (Módulo D).

Es la versión para leer o compartir del `report.json`: resumen, Risk Score,
hallazgos de mayor a menor gravedad e inventario criptográfico. Se arma con
`reportlab`, que se importa recién al generar el PDF para no ocupar memoria en
el worker cuando no hace falta.
"""

from collections import Counter
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from app.engines.base import Finding, Severity
from app.orchestrator.normalize import SEVERITY_ORDER
from app.orchestrator.pipeline import ScanResult
from app.storage.cyclonedx import algorithm_name

# Más hallazgos que esto no se listan: el PDF es un resumen, el detalle está en el JSON.
MAX_FINDINGS = 300

_SEVERITY_LABEL = {
    Severity.CRITICAL: "Crítica",
    Severity.HIGH: "Alta",
    Severity.MEDIUM: "Media",
    Severity.LOW: "Baja",
    Severity.INFO: "Informativa",
}
_SEVERITY_COLOR = {
    Severity.CRITICAL: "#c0262d",
    Severity.HIGH: "#c2581a",
    Severity.MEDIUM: "#a37a0b",
    Severity.LOW: "#3d6e9e",
    Severity.INFO: "#6b7280",
}
_ENGINE_LABEL = {"sast": "Código", "sca": "Dependencias", "secrets": "Secretos", "crypto": "Criptografía"}

# Las fuentes estándar de PDF solo tienen los caracteres de Windows-1252.
_REPLACEMENTS = {"≤": "<=", "≥": ">=", "→": "->", "…": "...", "—": "-", "–": "-", "“": '"', "”": '"'}


def build_pdf(scan_id: str, repo_url: str, commit_sha: str, result: ScanResult,
              generated_at: datetime | None = None) -> bytes:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    generated_at = generated_at or datetime.now(timezone.utc)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("cuerpo", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("chico", parent=body, fontSize=8, leading=10)
    h1 = ParagraphStyle("titulo", parent=styles["Title"], fontSize=18, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("seccion", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)

    def p(text: str, style=body) -> Paragraph:
        return Paragraph(_text(text), style)

    findings = list(result.findings.values())
    counts = Counter(f.severity for f in findings)
    story: list = [
        p("Reporte de seguridad · Qubitor", h1),
        p(f"<b>Repositorio:</b> {_esc(repo_url)}", body),
        p(f"<b>Commit:</b> {_esc(commit_sha[:12] or '-')} · <b>Escaneo:</b> {_esc(scan_id)}", body),
        p(f"<b>Generado:</b> {generated_at.strftime('%d/%m/%Y %H:%M')} UTC", body),
        Spacer(1, 4 * mm),
        p(f"<b>Risk Score:</b> {result.risk_score:g} / 100 · <b>Nota:</b> {_esc(result.grade)}", body),
    ]

    summary = [["Gravedad", "Hallazgos"]] + [[_SEVERITY_LABEL[s], str(counts.get(s, 0))] for s in SEVERITY_ORDER]
    table = Table(summary, colWidths=[40 * mm, 25 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story += [Spacer(1, 3 * mm), table]

    if result.errors:
        story.append(p("Motores con errores", h2))
        story += [p(f"<b>{_esc(_ENGINE_LABEL.get(engine, engine))}:</b> {_esc(error)}", small)
                  for engine, error in sorted(result.errors.items())]

    problems = sorted(
        (f for f in findings if f.severity != Severity.INFO),
        key=lambda f: (SEVERITY_ORDER.index(f.severity), f.engine, f.file_path, f.line or 0),
    )
    story.append(p("Hallazgos", h2))
    if not problems:
        story.append(p("No se encontraron problemas.", body))
    else:
        rows = [[p("<b>Gravedad</b>", small), p("<b>Hallazgo</b>", small), p("<b>Dónde</b>", small)]]
        for finding in problems[:MAX_FINDINGS]:
            rows.append([
                p(f'<font color="{_SEVERITY_COLOR[finding.severity]}"><b>{_SEVERITY_LABEL[finding.severity]}</b></font>', small),
                p(f"{_esc(finding.title)}<br/><font color='#6b7280'>{_esc(_reference(finding))}</font>", small),
                p(_esc(_location(finding)), small),
            ])
        findings_table = Table(rows, colWidths=[22 * mm, 98 * mm, 60 * mm], repeatRows=1)
        findings_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(findings_table)
        if len(problems) > MAX_FINDINGS:
            story.append(p(f"Se muestran {MAX_FINDINGS} de {len(problems)} hallazgos. El detalle completo está en el reporte JSON.", small))

    crypto = [f for f in findings if f.engine == "crypto"]
    story.append(p("Inventario criptográfico", h2))
    if crypto:
        algorithms = Counter(algorithm_name(f) for f in crypto)
        story.append(p(" · ".join(f"{_esc(name)} ({count})" for name, count in sorted(algorithms.items())), body))
        story.append(p("El inventario completo, en formato CycloneDX 1.6, está en el CBOM del escaneo.", small))
    else:
        story.append(p("No se detectó uso de criptografía.", body))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title="Reporte de seguridad - Qubitor", author="Qubitor",
    )
    doc.build(story)
    return buffer.getvalue()


def _reference(finding: Finding) -> str:
    parts = [_ENGINE_LABEL.get(finding.engine, finding.engine)]
    parts += [ref for ref in (finding.cve, finding.cwe) if ref]
    return " · ".join(parts)


def _location(finding: Finding) -> str:
    return f"{finding.file_path}:{finding.line}" if finding.line else finding.file_path


def _esc(value: object) -> str:
    """Escapa el texto para el mini-HTML de reportlab."""
    return escape(str(value))


def _text(text: str) -> str:
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    # Lo que la fuente no puede dibujar se reemplaza por "?" en vez de mostrarse como un cuadrado.
    return text.encode("cp1252", errors="replace").decode("cp1252")
