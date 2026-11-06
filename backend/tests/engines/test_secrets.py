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
    assert hallazgos[0].rule_id == "secrets.aws"
    assert hallazgos[0].severity == Severity.CRITICAL
    assert "AKIA1234567890ABCDEF" not in hallazgos[0].snippet
    assert "***" in hallazgos[0].snippet

def test_detecta_secreto_por_entropia(tmp_path):
    _escribir(tmp_path, "settings.py", "password = 'j8*kP9!xL2#mN5$qR8@vW3'")
    
    hallazgos = SecretsEngine().scan(str(tmp_path))
    
    assert len(hallazgos) == 1
    assert hallazgos[0].rule_id == "secrets.generic.entropy"

def test_ignora_carpetas_y_archivos_excluidos(tmp_path):
    _escribir(tmp_path, "node_modules/lib.js", "AWS_KEY = 'AKIA1234567890ABCDEF'")
    _escribir(tmp_path, "app.lock", "AKIA1234567890ABCDEF")
    
    hallazgos = SecretsEngine().scan(str(tmp_path))
    
    assert len(hallazgos) == 0