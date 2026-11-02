from app.engines.sca.manifests import Dependency, parse_requirements


# --- requirements.txt ---

def test_requirements_lee_versiones_exactas_con_su_linea():
    texto = (
        "# dependencias\n"
        "requests==2.19.0\n"
        "Flask == 1.0.2\n"
    )

    assert parse_requirements(texto, "requirements.txt") == [
        Dependency("requests", "2.19.0", "PyPI", "requirements.txt", 2),
        Dependency("Flask", "1.0.2", "PyPI", "requirements.txt", 3),
    ]


def test_requirements_acepta_extras_marcadores_y_comentarios_al_final():
    texto = "uvicorn[standard]==0.30.1 ; python_version >= '3.10'  # servidor\n"

    [dependencia] = parse_requirements(texto, "requirements.txt")

    assert (dependencia.name, dependencia.version) == ("uvicorn", "0.30.1")


def test_requirements_saltea_rangos_opciones_y_lineas_vacias():
    texto = (
        "\n"
        "requests>=2.0\n"
        "django~=4.2\n"
        "numpy\n"
        "-r otro-archivo.txt\n"
        "-e git+https://github.com/ejemplo/repo.git#egg=repo\n"
    )
    assert parse_requirements(texto, "requirements.txt") == []
