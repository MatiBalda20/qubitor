from app.engines.sca.manifests import (
    Dependency,
    parse_package_json,
    parse_package_lock,
    parse_requirements,
)


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


# --- package.json ---

def test_package_json_lee_dependencias_exactas_con_su_linea():
    texto = (
        "{\n"
        '  "name": "demo",\n'
        '  "dependencies": {\n'
        '    "lodash": "4.17.4"\n'
        "  },\n"
        '  "devDependencies": {\n'
        '    "jest": "29.7.0"\n'
        "  }\n"
        "}\n"
    )

    assert parse_package_json(texto, "package.json") == [
        Dependency("lodash", "4.17.4", "npm", "package.json", 4),
        Dependency("jest", "29.7.0", "npm", "package.json", 7),
    ]


def test_package_json_saltea_rangos():
    texto = '{"dependencies": {"a": "^4.17.4", "b": "~1.0.0", "c": ">=2.0.0", "d": "*", "e": "latest"}}'
    assert parse_package_json(texto, "package.json") == []


def test_package_json_invalido_no_rompe():
    assert parse_package_json("{ esto no es json", "package.json") == []
    assert parse_package_json("[1, 2, 3]", "package.json") == []


# --- package-lock.json ---

def test_package_lock_v3_lee_versiones_instaladas_incluso_anidadas():
    texto = (
        "{\n"
        '  "lockfileVersion": 3,\n'
        '  "packages": {\n'
        '    "": {"name": "demo"},\n'
        '    "node_modules/lodash": {"version": "4.17.4"},\n'
        '    "node_modules/express/node_modules/qs": {"version": "6.5.1"}\n'
        "  }\n"
        "}\n"
    )

    assert parse_package_lock(texto, "package-lock.json") == [
        Dependency("lodash", "4.17.4", "npm", "package-lock.json", 5),
        Dependency("qs", "6.5.1", "npm", "package-lock.json", 6),
    ]


def test_package_lock_v1():
    texto = '{"lockfileVersion": 1, "dependencies": {"lodash": {"version": "4.17.4"}}}'

    [dependencia] = parse_package_lock(texto, "package-lock.json")

    assert (dependencia.name, dependencia.version) == ("lodash", "4.17.4")


def test_package_lock_no_repite_la_misma_version():
    texto = (
        '{"packages": {'
        '"node_modules/a/node_modules/lodash": {"version": "4.17.4"},'
        '"node_modules/b/node_modules/lodash": {"version": "4.17.4"}'
        "}}"
    )
    assert len(parse_package_lock(texto, "package-lock.json")) == 1


def test_package_lock_mal_formado_no_rompe():
    assert parse_package_lock('{"dependencies": [1, 2]}', "package-lock.json") == []
    assert parse_package_lock('{"packages": {"node_modules/x": "1.0.0"}}', "package-lock.json") == []
