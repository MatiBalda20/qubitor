from app.engines.sca.manifests import (
    Dependency,
    find_dependencies,
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


# --- Búsqueda en el repo ---

def test_busca_dependencias_en_todo_el_repo(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.19.0\n")
    (tmp_path / "requirements-dev.txt").write_text("pytest==7.0.0\n")
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "package.json").write_text('{"dependencies": {"lodash": "4.17.4"}}')

    encontradas = [(d.file_path, d.name) for d in find_dependencies(str(tmp_path))]

    assert encontradas == [
        ("requirements-dev.txt", "pytest"),
        ("requirements.txt", "requests"),
        ("web/package.json", "lodash"),
    ]


def test_si_hay_lock_se_usa_el_lock_y_no_el_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"lodash": "4.17.4"}}')
    (tmp_path / "package-lock.json").write_text(
        '{"packages": {"node_modules/lodash": {"version": "4.17.21"}}}'
    )

    [dependencia] = find_dependencies(str(tmp_path))

    assert (dependencia.file_path, dependencia.version) == ("package-lock.json", "4.17.21")


def test_ignora_dependencias_de_librerias_descargadas(tmp_path):
    (tmp_path / "node_modules" / "lodash").mkdir(parents=True)
    (tmp_path / "node_modules" / "lodash" / "package.json").write_text(
        '{"dependencies": {"x": "1.0.0"}}'
    )
    assert find_dependencies(str(tmp_path)) == []


def test_no_sigue_enlaces_a_archivos_de_afuera_del_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    afuera = tmp_path / "requirements.txt"
    afuera.write_text("secreto==1.0.0\n")
    (repo / "requirements.txt").symlink_to(afuera)

    assert find_dependencies(str(repo)) == []
