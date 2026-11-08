from app.engines.base import Severity
from app.engines.sca.findings import fixed_version, vulnerability_to_finding
from app.engines.sca.manifests import Dependency
from app.orchestrator.normalize import deduplicate

REQUESTS = Dependency("requests", "2.19.0", "PyPI", "requirements.txt", 3)
LODASH = Dependency("lodash", "4.17.4", "npm", "package.json", 7)

# Recorte de la respuesta real de OSV para GHSA-x84v-xcm2-53pg.
GHSA_REQUESTS = {
    "id": "GHSA-x84v-xcm2-53pg",
    "aliases": ["CVE-2018-18074", "PYSEC-2018-28"],
    "summary": "Insufficiently Protected Credentials in Requests",
    "details": "The Requests package through 2.19.1 sends an HTTP Authorization header ...",
    "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"}],
    "database_specific": {"severity": "HIGH", "cwe_ids": ["CWE-522"]},
    "affected": [{
        "package": {"name": "requests", "ecosystem": "PyPI"},
        "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.20.0"}]}],
    }],
}


def _afectado(nombre, ecosistema, *rangos):
    return {
        "package": {"name": nombre, "ecosystem": ecosistema},
        "ranges": [
            {"type": "ECOSYSTEM", "events": [{"introduced": desde}, {"fixed": hasta}]}
            for desde, hasta in rangos
        ],
    }


def test_convierte_la_vulnerabilidad_en_un_hallazgo_completo():
    h = vulnerability_to_finding(REQUESTS, GHSA_REQUESTS)

    assert h.engine == "sca"
    assert h.rule_id == "sca.osv.GHSA-x84v-xcm2-53pg"
    assert h.severity == Severity.HIGH
    assert h.cve == "CVE-2018-18074"
    assert h.cwe == "CWE-522"
    assert (h.file_path, h.line) == ("requirements.txt", 3)
    assert h.snippet == "requests==2.19.0"
    assert h.title == "requests 2.19.0: Insufficiently Protected Credentials in Requests"
    assert "pip install requests==2.20.0" in h.description
    assert h.metadata["fixed_version"] == "2.20.0"
    assert h.metadata["upgrade_command"] == "pip install requests==2.20.0"
    assert h.metadata["cvss_vector"].startswith("CVSS:3.1/")
    assert h.metadata["severity_source"] == "github"


def test_varias_fallas_del_mismo_paquete_sobreviven_a_la_deduplicacion():
    fallas = [
        {"id": "GHSA-jf85-cpcp-j695", "aliases": ["CVE-2019-10744"], "database_specific": {"severity": "CRITICAL"}},
        {"id": "GHSA-p6mc-m468-83gw", "aliases": ["CVE-2020-8203"], "database_specific": {"severity": "HIGH"}},
    ]

    hallazgos = [vulnerability_to_finding(LODASH, falla) for falla in fallas]

    assert [h.cve for h in deduplicate(hallazgos).values()] == ["CVE-2019-10744", "CVE-2020-8203"]


def test_npm_arma_el_comando_y_el_snippet_de_npm():
    vuln = {"id": "GHSA-jf85-cpcp-j695", "aliases": ["CVE-2019-10744"],
            "database_specific": {"severity": "CRITICAL"},
            "affected": [_afectado("lodash", "npm", ("0", "4.17.12"))]}

    h = vulnerability_to_finding(LODASH, vuln)

    assert h.severity == Severity.CRITICAL
    assert h.snippet == '"lodash": "4.17.4"'
    assert h.metadata["upgrade_command"] == "npm install lodash@4.17.12"


def test_moderate_de_github_es_medium_y_sin_gravedad_queda_medium_marcada():
    moderada = {"id": "A", "database_specific": {"severity": "MODERATE"}}
    sin_gravedad = {"id": "PYSEC-2018-28", "aliases": ["CVE-2018-18074"]}

    assert vulnerability_to_finding(REQUESTS, moderada).severity == Severity.MEDIUM
    h = vulnerability_to_finding(REQUESTS, sin_gravedad)
    assert h.severity == Severity.MEDIUM
    assert h.metadata["severity_source"] == "desconocida"


def test_sin_version_corregida_lo_dice_y_no_hay_comando():
    h = vulnerability_to_finding(REQUESTS, {"id": "A", "affected": []})

    assert h.metadata["fixed_version"] is None
    assert h.metadata["upgrade_command"] is None
    assert "Todavía no hay una versión corregida" in h.description


# --- Versión corregida ---

def test_elige_la_correccion_de_la_rama_instalada():
    # Corregida en 3.5 (rama 3.x) y en 4.2 (rama 4.x): a la 4.1 le sirve la 4.2.
    vuln = {"affected": [_afectado("paquete", "PyPI", ("3.0", "3.5"), ("4.0", "4.2"))]}
    instalada = Dependency("paquete", "4.1", "PyPI", "requirements.txt", 1)

    assert fixed_version(vuln, instalada) == "4.2"


def test_compara_versiones_como_numeros_y_no_como_texto():
    # Como texto, "4.17.12" < "4.17.5"; como números, 12 > 5.
    vuln = {"affected": [_afectado("lodash", "npm", ("0", "4.17.12"), ("0", "4.17.5"))]}
    assert fixed_version(vuln, LODASH) == "4.17.5"


def test_ignora_paquetes_de_otro_ecosistema_y_rangos_de_git():
    vuln = {"affected": [
        _afectado("requests", "npm", ("0", "9.9.9")),
        {"package": {"name": "requests", "ecosystem": "PyPI"},
         "ranges": [{"type": "GIT", "events": [{"fixed": "c45d7c49ea75"}]}]},
    ]}
    assert fixed_version(vuln, REQUESTS) is None


def test_el_nombre_en_pypi_no_distingue_mayusculas_ni_guiones():
    vuln = {"affected": [_afectado("Python_Jose", "PyPI", ("0", "3.4.0"))]}
    instalada = Dependency("python-jose", "3.3.0", "PyPI", "requirements.txt", 1)

    assert fixed_version(vuln, instalada) == "3.4.0"


def test_campos_nulos_de_osv_no_rompen():
    vuln = {"id": "PYSEC-2018-28", "aliases": None, "summary": None, "details": None,
            "severity": None, "database_specific": None, "affected": None}

    h = vulnerability_to_finding(REQUESTS, vuln)

    assert h.cve is None
    assert h.title == "requests 2.19.0 tiene una vulnerabilidad conocida"
