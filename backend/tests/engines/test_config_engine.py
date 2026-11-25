from app.engines.base import Severity
from app.engines.config import ConfigEngine


def test_detecta_dockerfile_con_user_root(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim\nUSER root\nCMD ['python']\n")
    hallazgos = ConfigEngine().scan(str(tmp_path))

    assert [(h.rule_id, h.line, h.severity) for h in hallazgos] == [
        ("config.docker.root-user", 2, Severity.HIGH),
    ]


def test_dockerfile_con_usuario_no_root_no_reporta(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim\nUSER appuser\n")
    assert ConfigEngine().scan(str(tmp_path)) == []


def test_detecta_nginx_tls_y_ciphers_debiles(tmp_path):
    (tmp_path / "nginx.conf").write_text(
        "server {\n"
        "  ssl_protocols TLSv1 TLSv1.2;\n"
        "  ssl_ciphers HIGH:RC4:MD5;\n"
        "}\n"
    )
    reglas = [h.rule_id for h in ConfigEngine().scan(str(tmp_path))]
    assert reglas == ["config.nginx.tls-insecure", "config.nginx.weak-cipher"]


def test_detecta_compose_puerto_expuesto_y_privileged(tmp_path):
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n"
        "  db:\n"
        "    privileged: true\n"
        "    ports:\n"
        "      - '5432:5432'\n"
    )
    reglas = [h.rule_id for h in ConfigEngine().scan(str(tmp_path))]
    assert reglas == ["config.compose.privileged", "config.compose.exposed-port"]


def test_detecta_terraform_cidr_abierto(tmp_path):
    (tmp_path / "main.tf").write_text('cidr_blocks = ["0.0.0.0/0"]\n')
    hallazgos = ConfigEngine().scan(str(tmp_path))
    assert [h.rule_id for h in hallazgos] == ["config.terraform.public-cidr"]