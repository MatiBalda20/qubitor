import threading
import time

from app.engines.base import Engine, Finding, Severity
from app.orchestrator.runner import run_engines


def _finding(engine):
    return Finding(
        engine=engine,
        rule_id=f"{engine}.regla",
        title="",
        severity=Severity.LOW,
        file_path="a.py",
        line=1,
        snippet="",
        description="",
    )


class MotorOk(Engine):
    def __init__(self, name, demora=0.0):
        self.name = name
        self.demora = demora

    def scan(self, repo_path):
        time.sleep(self.demora)
        return [_finding(self.name)]


class MotorQueFalla(Engine):
    name = "roto"

    def scan(self, repo_path):
        raise RuntimeError("no anda")


class MotorColgado(Engine):
    name = "colgado"

    def __init__(self):
        self.liberar = threading.Event()

    def scan(self, repo_path):
        self.liberar.wait(5)
        return [_finding(self.name)]


def test_sin_motores():
    resultado = run_engines([], "repo")
    assert resultado.findings == []
    assert resultado.errors == {}


def test_junta_los_hallazgos_de_todos_los_motores():
    resultado = run_engines([MotorOk("sast"), MotorOk("sca")], "repo")
    assert sorted(h.engine for h in resultado.findings) == ["sast", "sca"]
    assert resultado.errors == {}


def test_corre_en_paralelo():
    inicio = time.monotonic()
    run_engines([MotorOk(f"m{i}", demora=0.3) for i in range(4)], "repo")
    assert time.monotonic() - inicio < 1.0


def test_un_motor_que_falla_no_frena_a_los_demas():
    resultado = run_engines([MotorQueFalla(), MotorOk("sast")], "repo")
    assert [h.engine for h in resultado.findings] == ["sast"]
    assert resultado.errors == {"roto": "RuntimeError: no anda"}


def test_un_motor_colgado_se_corta_por_timeout():
    colgado = MotorColgado()
    inicio = time.monotonic()
    resultado = run_engines([colgado, MotorOk("sast")], "repo", timeout=0.2)
    colgado.liberar.set()

    assert time.monotonic() - inicio < 1.0
    assert [h.engine for h in resultado.findings] == ["sast"]
    assert "límite de 0.2 s" in resultado.errors["colgado"]


def test_pasa_la_ruta_del_repo_a_cada_motor():
    rutas = []

    class MotorEspia(Engine):
        name = "espia"

        def scan(self, repo_path):
            rutas.append(repo_path)
            return []

    run_engines([MotorEspia()], "/tmp/scan-1")
    assert rutas == ["/tmp/scan-1"]
