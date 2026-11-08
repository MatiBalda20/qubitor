import os

import pytest

from app.engines.base import Engine, Severity
from app.engines.sca import ScaEngine


class OsvFalso:
    """Reemplaza a OsvClient con datos fijos y cuenta los pedidos."""

    def __init__(self, ids_por_paquete, detalles):
        self.ids_por_paquete = ids_por_paquete
        self.detalles = detalles
        self.consultas = 0
        self.detalles_pedidos = []

    def query_batch(self, dependencias):
        self.consultas += 1
        return [self.ids_por_paquete.get(d.name, []) for d in dependencias]

    def get_vuln(self, vuln_id):
        self.detalles_pedidos.append(vuln_id)
        return self.detalles[vuln_id]

    def get_vulns(self, vuln_ids):
        return {vuln_id: self.get_vuln(vuln_id) for vuln_id in vuln_ids}


GHSA = {"id": "GHSA-x84v-xcm2-53pg", "aliases": ["CVE-2018-18074", "PYSEC-2018-28"],
        "database_specific": {"severity": "HIGH"}}
PYSEC = {"id": "PYSEC-2018-28", "aliases": ["CVE-2018-18074", "GHSA-x84v-xcm2-53pg"]}


def test_es_un_motor_del_contrato():
    motor = ScaEngine(OsvFalso({}, {}))
    assert isinstance(motor, Engine)
    assert motor.name == "sca"


def test_la_misma_falla_con_dos_ids_aparece_una_sola_vez_con_su_gravedad(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.19.0\n")
    osv = OsvFalso({"requests": ["PYSEC-2018-28", "GHSA-x84v-xcm2-53pg"]},
                   {"PYSEC-2018-28": PYSEC, "GHSA-x84v-xcm2-53pg": GHSA})

    [hallazgo] = ScaEngine(osv).scan(str(tmp_path))

    assert hallazgo.cve == "CVE-2018-18074"
    assert hallazgo.severity == Severity.HIGH
    assert hallazgo.metadata["vuln_id"] == "GHSA-x84v-xcm2-53pg"


def test_cada_vulnerabilidad_se_pide_una_sola_vez(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.19.0\n")
    (tmp_path / "requirements-dev.txt").write_text("requests==2.19.0\n")
    osv = OsvFalso({"requests": ["GHSA-x84v-xcm2-53pg"]}, {"GHSA-x84v-xcm2-53pg": GHSA})

    hallazgos = ScaEngine(osv).scan(str(tmp_path))

    assert len(hallazgos) == 2                                  # uno por archivo
    assert osv.detalles_pedidos == ["GHSA-x84v-xcm2-53pg"]      # pero un solo pedido


def test_sin_archivos_de_dependencias_no_consulta_osv(tmp_path):
    osv = OsvFalso({}, {})

    assert ScaEngine(osv).scan(str(tmp_path)) == []
    assert osv.consultas == 0


@pytest.mark.skipif(os.environ.get("QUBITOR_TESTS_RED") != "1",
                    reason="usa internet; correr con QUBITOR_TESTS_RED=1")
def test_contra_osv_real_detecta_las_fallas_del_repo_de_demo(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.19.0\n")
    (tmp_path / "package.json").write_text('{"dependencies": {"lodash": "4.17.4"}}')

    cves = {h.cve for h in ScaEngine().scan(str(tmp_path))}

    assert {"CVE-2018-18074", "CVE-2019-10744"} <= cves
