import pytest

from app.engines.sca.cvss import base_score


@pytest.mark.parametrize("vector, esperado", [
    # Puntajes publicados por NVD para cada vector.
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N", 7.5),  # CVE-2018-18074, requests
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H", 9.1),  # CVE-2019-10744, lodash
    ("CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:H/A:H", 7.4),  # CVE-2020-8203, lodash
    ("CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:C/C:H/I:N/A:N", 6.1),  # CVE-2023-32681, requests
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H", 9.9),
    ("CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
])
def test_calcula_el_puntaje_base(vector, esperado):
    assert base_score(vector) == esperado


def test_sin_impacto_el_puntaje_es_cero():
    assert base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N") == 0.0


def test_ignora_las_metricas_temporales():
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N/E:P/RL:O"
    assert base_score(vector) == 7.5


@pytest.mark.parametrize("vector", [
    "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:L/SC:N/SI:N/SA:N",
    "AV:N/AC:L/Au:N/C:P/I:P/A:P",  # CVSS 2
    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H",  # falta A
    "CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",  # valor inválido
    "CVSS:3.1/AV",
    "",
])
def test_vectores_que_no_se_pueden_calcular_devuelven_none(vector):
    assert base_score(vector) is None
