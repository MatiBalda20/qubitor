import fakeredis
import pytest
from rq.serializers import JSONSerializer

from app.orchestrator.pipeline import analyze_repository
from app.worker import job as job_module
from app.worker import progress
from app.worker.progress import STAGE_PROGRESS, read_progress, report_stage
from app.worker.queue import QUEUE_NAME, enqueue_scan
from app.worker.run import _NoForkWorker

FRONTEND_STAGES = ["clone", "engines", "normalize", "triage", "score", "persist"]


def test_las_etapas_son_las_del_frontend_y_el_porcentaje_avanza():
    assert list(STAGE_PROGRESS) == FRONTEND_STAGES
    porcentajes = list(STAGE_PROGRESS.values())
    assert porcentajes == sorted(porcentajes)
    assert 0 < porcentajes[0] and porcentajes[-1] < 100


def test_el_pipeline_avisa_cada_etapa_en_orden(tmp_path):
    etapas = []
    analyze_repository(str(tmp_path), [], on_stage=etapas.append)
    assert etapas == ["engines", "normalize", "score"]


def test_fuera_de_un_trabajo_no_hace_nada():
    report_stage("clone")  # no lanza


@pytest.fixture
def redis():
    return fakeredis.FakeStrictRedis()


def test_sin_trabajo_en_redis_no_hay_progreso(redis):
    assert read_progress("no-existe", connection=redis) == (None, None)


def test_si_redis_no_responde_no_hay_progreso(monkeypatch):
    def caido():
        raise ConnectionError("Redis caído")

    monkeypatch.setattr(progress, "get_connection", caido)
    assert read_progress("abc") == (None, None)


def test_etapa_desconocida_se_ignora(redis):
    trabajo = enqueue_scan("abc", "https://github.com/a/b", connection=redis)
    trabajo.meta.update(stage="inventada", progress=50)
    trabajo.save_meta()

    assert read_progress("abc", connection=redis) == (None, None)


def test_el_worker_informa_las_etapas_y_la_api_las_lee(redis, monkeypatch, tmp_path):
    """Recorre un escaneo real en la cola y registra lo que se lee en cada etapa."""
    leidas = []
    original = progress.report_stage

    def report_y_leer(stage):
        original(stage)
        leidas.append(read_progress("abc", connection=redis))

    class Store:
        def mark_running(self, scan_id): ...
        def save_result(self, scan_id, commit_sha, result): ...
        def mark_failed(self, scan_id, error): raise AssertionError(error)

    def clon_falso(url, destino):
        (tmp_path / "repo").mkdir()
        return "a" * 40

    monkeypatch.setattr(job_module, "report_stage", report_y_leer)
    monkeypatch.setattr(job_module, "get_store", lambda: Store())
    monkeypatch.setattr(job_module, "clone_repository", clon_falso)
    monkeypatch.setattr(job_module, "default_engines", lambda: [])
    monkeypatch.setattr(job_module, "archive_scan", lambda *args: False)
    monkeypatch.setattr(job_module.tempfile, "mkdtemp", lambda **kwargs: str(tmp_path))
    monkeypatch.setattr(job_module, "remove_tree", lambda path: None)

    enqueue_scan("abc", "https://github.com/a/b", connection=redis)
    _NoForkWorker([QUEUE_NAME], connection=redis, serializer=JSONSerializer).work(burst=True, with_scheduler=False)

    assert leidas == [(stage, STAGE_PROGRESS[stage]) for stage in ["clone", "engines", "normalize", "score", "persist"]]
