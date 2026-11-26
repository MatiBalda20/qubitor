import time

import pytest
from app.engines.base import Severity
from app.engines.secrets.engine import SecretsEngine

def _escribir(repo, ruta, contenido):
    archivo = repo / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")

def test_detecta_token_aws_y_enmascara_valor(tmp_path):
    _escribir(tmp_path, "config.py", "AWS_KEY = 'AKIA1234567890ABCDEF'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert "AKIA1234567890ABCDEF" not in hallazgos[0].snippet
    assert "***" in hallazgos[0].snippet

def test_detecta_secreto_por_entropia(tmp_path):
    # Usando el string sugerido de 32 caracteres para asegurar entropía > 4.5
    _escribir(tmp_path, "settings.py", "password = 'qL7xV2mR9tK4wZ8pN3sF6hJ1cB5dG0yE'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert hallazgos[0].rule_id == "secrets.generic.entropy"

def test_ignora_baja_entropia(tmp_path):
    _escribir(tmp_path, "baja_entropia.py", "password = 'aaaaaaaaaaaaaaaaaaaaaaaaa'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 0

def test_enmascara_multiples_secretos_en_una_linea(tmp_path):
    _escribir(tmp_path, "multi.py", "AWS_KEY = 'AKIA1234567890ABCDEF'; OTHER = 'AKIA0987654321UVWXYZ'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 2
    # El snippet de ambos debe tener los dos secretos censurados
    assert "AKIA" not in hallazgos[0].snippet
    assert hallazgos[0].snippet.count("***") == 2

def test_no_duplica_hallazgos_por_token_conocido(tmp_path):
    _escribir(tmp_path, "github.py", "GITHUB_TOKEN = 'ghp_123456789012345678901234567890123456'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert hallazgos[0].rule_id == "secrets.github"

def test_detecta_secretos_genericos_sin_comillas_y_en_diccionarios(tmp_path):
    _escribir(tmp_path, ".env", "secret_value=qL7xV2mR9tK4wZ8pN3sF6hJ1cB5dG0yE")
    _escribir(tmp_path, "config.json", "{'api_token': 'qL7xV2mR9tK4wZ8pN3sF6hJ1cB5dG0yE'}")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 2

def test_linea_larga_no_cuelga_el_motor(tmp_path):
    _escribir(tmp_path, "blob.txt", "a" * 20000)
    inicio = time.monotonic()
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert time.monotonic() - inicio < 1
    assert len(hallazgos) == 0

@pytest.mark.parametrize("linea", [
    "TOKEN_URL=https://auth.Example.com/oauth2/V1/Token?client=ABC123xyz&scope=Read_Write&aud=Zq9",
    "secret_key=Settings.getSecretValue(Vault.Client(URL_X),Path.join(BASE,'a'))",
    "const tokenMap:Record<string,AuthTokenResponse|RefreshPayload|Null_Value>=new Map();",
    "--key: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk",
])
def test_no_reporta_urls_ni_codigo_como_secreto(tmp_path, linea):
    _escribir(tmp_path, "config.txt", linea)
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 0

@pytest.mark.parametrize("separador", ["}", "]"])
def test_enmascara_entero_un_secreto_con_llaves_o_corchetes(tmp_path, separador):
    _escribir(tmp_path, "settings.py", f"password = 'aB3dE6gH9jK2mN5pQ8sT1vW4yZ7cF0{separador}SECRETORESTANTE'")
    hallazgos = SecretsEngine().scan(str(tmp_path))
    assert len(hallazgos) == 1
    assert "SECRETORESTANTE" not in hallazgos[0].snippet

def test_detecta_secreto_borrado_en_historial_de_git(tmp_path):
    import subprocess

    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init")
    git("config", "user.email", "test@qubitor.invalid")
    git("config", "user.name", "Test")

    archivo = tmp_path / "config.py"
    archivo.write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    git("add", "config.py")
    git("commit", "-m", "agregar secreto")

    # Borramos el secreto en un segundo commit
    archivo.write_text('AWS_KEY = ""\n')
    git("add", "config.py")
    git("commit", "-m", "borrar secreto")

    hallazgos = SecretsEngine().scan(str(tmp_path))
    reglas = [h.rule_id for h in hallazgos]
    assert "secrets.aws.history" in reglas
    assert all("AKIAIOSFODNN7EXAMPLE" not in h.snippet for h in hallazgos)

def test_clon_superficial_no_duplica_secreto_en_head(tmp_path):
    import subprocess

    origen = tmp_path / "origen"
    origen.mkdir()

    def git(cwd, *args):
        subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)

    git(origen, "init")
    git(origen, "config", "user.email", "test@qubitor.invalid")
    git(origen, "config", "user.name", "Test")

    (origen / "app.py").write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    git(origen, "add", "app.py")
    git(origen, "commit", "-m", "commit inicial")

    clon = tmp_path / "clon"
    subprocess.run(
        ["git", "clone", "--depth", "1", f"file://{origen.as_posix()}", str(clon)],
        check=True,
        capture_output=True,
    )

    hallazgos = SecretsEngine().scan(str(clon))
    reglas = [h.rule_id for h in hallazgos]
    assert "secrets.aws" in reglas
    assert "secrets.aws.history" not in reglas

def test_clon_superficial_detecta_secreto_borrado_con_deepen(tmp_path):
    import subprocess

    origen = tmp_path / "origen"
    origen.mkdir()

    def git(cwd, *args):
        subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)

    git(origen, "init")
    git(origen, "config", "user.email", "test@qubitor.invalid")
    git(origen, "config", "user.name", "Test")

    archivo = origen / "config.py"
    archivo.write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    git(origen, "add", "config.py")
    git(origen, "commit", "-m", "agregar secreto")

    archivo.write_text('AWS_KEY = ""\n')
    git(origen, "add", "config.py")
    git(origen, "commit", "-m", "borrar secreto")

    clon = tmp_path / "clon"
    subprocess.run(
        ["git", "clone", "--depth", "1", f"file://{origen.as_posix()}", str(clon)],
        check=True,
        capture_output=True,
    )

    hallazgos = SecretsEngine().scan(str(clon))
    history = [h for h in hallazgos if h.rule_id == "secrets.aws.history"]
    assert len(history) == 1
    assert history[0].line == 1


# Límites del historial de Git (QUB-03): nunca un "escaneo limpio" si no se pudo mirar.

def _git(cwd, *args):
    import subprocess

    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def _origen_con_historial(tmp_path, *contenidos):
    origen = tmp_path / "origen"
    origen.mkdir()
    _git(origen, "init")
    _git(origen, "config", "user.email", "test@qubitor.invalid")
    _git(origen, "config", "user.name", "Test")
    for n, contenido in enumerate(contenidos):
        (origen / "config.py").write_bytes(contenido if isinstance(contenido, bytes) else contenido.encode())
        _git(origen, "add", "config.py")
        _git(origen, "commit", "-m", f"commit {n}")
    return origen


def _clon_superficial(tmp_path, origen):
    import subprocess

    clon = tmp_path / "clon"
    subprocess.run(
        ["git", "clone", "--depth", "1", f"file://{origen.as_posix()}", str(clon)], check=True, capture_output=True
    )
    return clon


def _aviso(hallazgos):
    return [h for h in hallazgos if h.rule_id == "secrets.history.incomplete"]


def test_historial_que_pasa_el_limite_del_repo_se_corta_y_se_avisa(tmp_path, monkeypatch):
    from app.engines.secrets import engine

    origen = _origen_con_historial(tmp_path, 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n', 'AWS_KEY = ""\n')
    clon = _clon_superficial(tmp_path, origen)
    # El clon superficial entra en el límite; el historial completo no.
    monkeypatch.setattr(engine, "MAX_REPO_BYTES", engine._size_of(str(clon)) + 10)

    hallazgos = SecretsEngine().scan(str(clon))

    avisos = _aviso(hallazgos)
    assert len(avisos) == 1
    assert avisos[0].severity == Severity.INFO
    assert "50 MB" in avisos[0].description
    assert not [h for h in hallazgos if h.rule_id == "secrets.aws.history"]


def test_salida_del_historial_con_tope_de_bytes_avisa_y_conserva_lo_leido(tmp_path, monkeypatch):
    from app.engines.secrets import engine

    relleno = "".join(f"linea_{n} = {n}\n" for n in range(2000))
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@qubitor.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    for n, contenido in enumerate(['AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n', relleno, 'AWS_KEY = ""\n']):
        (tmp_path / f"f{n}.py").write_text(contenido, encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"commit {n}")
    monkeypatch.setattr(engine, "HISTORY_MAX_OUTPUT_BYTES", 4096)

    hallazgos = SecretsEngine().scan(str(tmp_path))

    assert len(_aviso(hallazgos)) == 1
    assert "MB de cambios" in _aviso(hallazgos)[0].description


def test_una_linea_gigante_en_el_historial_no_se_carga_entera(tmp_path, monkeypatch):
    from app.engines.secrets import engine

    gigante = "x = '" + "a" * 20_000 + "'\n"
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@qubitor.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    for n, contenido in enumerate([gigante + 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n', 'AWS_KEY = ""\n']):
        (tmp_path / "config.py").write_text(contenido, encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"commit {n}")
    monkeypatch.setattr(engine, "HISTORY_MAX_LINE_BYTES", 256)

    hallazgos = SecretsEngine().scan(str(tmp_path))

    historial = [h for h in hallazgos if h.rule_id == "secrets.aws.history"]
    assert len(historial) == 1
    assert historial[0].line == 2  # la línea gigante se saltea pero se cuenta
    assert not _aviso(hallazgos)


def test_si_git_log_falla_se_avisa_en_lugar_de_devolver_vacio(tmp_path, monkeypatch):
    from app.engines.secrets import engine

    origen = _origen_con_historial(tmp_path, 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n', 'AWS_KEY = ""\n')

    def git_no_esta(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(engine.subprocess, "Popen", git_no_esta)
    monkeypatch.setattr(engine, "_commit_count", lambda repo: 2)

    hallazgos = SecretsEngine()._scan_git_history(origen)

    assert len(_aviso(hallazgos)) == 1


def test_repo_de_un_solo_commit_no_genera_aviso(tmp_path):
    origen = _origen_con_historial(tmp_path, 'x = 1\n')

    assert SecretsEngine()._scan_git_history(origen) == []
