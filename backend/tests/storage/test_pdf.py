import io
from datetime import datetime, timezone

from pypdf import PdfReader

from app.engines.base import Finding, Severity
from app.orchestrator.pipeline import ScanResult
from app.storage.pdf import MAX_FINDINGS, build_pdf


def _hallazgo(engine, rule_id, severity, file_path, line, title, algorithm=None, cve=None, cwe=None):
    return Finding(
        engine=engine, rule_id=rule_id, title=title, severity=severity, file_path=file_path, line=line,
        snippet="...", description="...", cve=cve, cwe=cwe,
        metadata={"algorithm": algorithm} if algorithm else {},
    )


def _resultado(hallazgos, errores=None, score=42.5, nota="D"):
    return ScanResult(
        findings={f"fp{i}": h for i, h in enumerate(hallazgos)},
        errors=errores or {}, risk_score=score, grade=nota, duration_seconds=3.0, engine_count=4,
    )


def _texto(pdf: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)


DEMO = [
    _hallazgo("sca", "sca.osv.GHSA-x84v-xcm2-53pg", Severity.HIGH, "requirements.txt", 1,
              "requests 2.19.0: credenciales enviadas por HTTP", cve="CVE-2018-18074"),
    _hallazgo("crypto", "crypto.pqc.rsa-keygen", Severity.MEDIUM, "app/keys.py", 10,
              "Generación de clave RSA vulnerable a computación cuántica", "RSA", cwe="CWE-327"),
    _hallazgo("crypto", "crypto.pqc.aes-128", Severity.LOW, "app/keys.py", 20,
              "Cifrado AES-128 debilitado por computación cuántica", "AES-128"),
    _hallazgo("crypto", "crypto.pqc.inventory.hash", Severity.INFO, "app/keys.py", 25,
              "Uso de SHA-256 (inventario criptográfico)", "SHA-256"),
]


def test_el_pdf_tiene_el_resumen_los_hallazgos_y_el_inventario():
    pdf = build_pdf("scan1", "https://github.com/org/repo", "abc123def4567890", _resultado(DEMO),
                    generated_at=datetime(2026, 11, 8, 15, 30, tzinfo=timezone.utc))

    assert pdf.startswith(b"%PDF")
    texto = _texto(pdf)
    assert "Reporte de seguridad" in texto
    assert "https://github.com/org/repo" in texto
    assert "abc123def456" in texto and "abc123def4567890" not in texto
    assert "08/11/2026 15:30" in texto
    assert "Risk Score: 42.5 / 100" in texto and "Nota: D" in texto
    # Los acentos se ven bien con las fuentes estándar.
    assert "Generación de clave RSA vulnerable a computación cuántica" in texto
    assert "CVE-2018-18074" in texto and "app/keys.py:10" in texto
    # El inventario va aparte, no como hallazgo.
    assert "Uso de SHA-256" not in texto
    assert "AES-128 (1)" in texto and "RSA (1)" in texto and "SHA-256 (1)" in texto


def test_los_hallazgos_van_de_mas_grave_a_menos_grave():
    texto = _texto(build_pdf("scan1", "url", "sha", _resultado(list(reversed(DEMO)))))

    assert texto.index("requests 2.19.0") < texto.index("Generación de clave RSA") < texto.index("Cifrado AES-128")


def test_sin_problemas_lo_dice():
    texto = _texto(build_pdf("scan1", "url", "sha", _resultado([], score=100, nota="A")))

    assert "No se encontraron problemas." in texto
    assert "No se detectó uso de criptografía." in texto


def test_muestra_los_motores_que_fallaron():
    texto = _texto(build_pdf("scan1", "url", "sha", _resultado(DEMO, errores={"secrets": "TimeoutError"})))

    assert "Motores con errores" in texto and "Secretos: TimeoutError" in texto


def test_con_muchos_hallazgos_lista_un_maximo_y_avisa():
    muchos = [_hallazgo("sast", f"sast.r{i}", Severity.LOW, f"app/f{i}.py", i, f"Hallazgo {i}")
              for i in range(MAX_FINDINGS + 5)]

    texto = _texto(build_pdf("scan1", "url", "sha", _resultado(muchos)))

    assert f"Se muestran {MAX_FINDINGS} de {MAX_FINDINGS + 5} hallazgos" in texto


def test_texto_con_marcas_y_caracteres_raros_no_rompe_el_pdf():
    raro = _hallazgo("sast", "sast.x", Severity.HIGH, "app/<script>.py", 1, "eval(x) & <b>sin cerrar ≤ → 🔥")

    texto = _texto(build_pdf("scan1", "url", "sha", _resultado([raro])))

    assert "eval(x) & <b>sin cerrar <= ->" in texto
    assert "app/<script>.py:1" in texto
