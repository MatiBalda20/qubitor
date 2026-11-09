# Módulo E — Integración con GitHub

Conecta Qubitor con los repositorios de GitHub del usuario: lista sus repos, valida y conecta el que elige, y le permite al scan-worker clonarlo, también si es privado.

## Cómo funciona

```
Navegador ──JWT de Clerk──▶ API ──CLERK_SECRET_KEY──▶ Clerk Backend API ──▶ token OAuth de GitHub
                             │                                                  │
                             └────────── Bearer <token de GitHub> ──────────────┴──▶ api.github.com
```

- El **JWT de sesión de Clerk** prueba quién es el usuario ante la API de Qubitor. No sirve para GitHub.
- El **token OAuth de GitHub** lo guarda Clerk cuando el usuario inicia sesión con GitHub. El backend lo pide en cada request a `GET https://api.clerk.com/v1/users/{user_id}/oauth_access_tokens/{proveedor}` y lo descarta. Nunca llega al frontend ni se guarda en la base.
- **Repos privados:** el trabajo de la cola solo lleva `scan_id` y la URL. El worker busca quién conectó el repo (`repositories.connected_by_user_id`) y le pide el token a Clerk en el momento del clonado.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/github/repositories?page=1&per_page=30` | Repos que el usuario puede leer (propios, de colaborador y de sus organizaciones), ordenados por actividad. Cada uno trae `connected` (ya lo conectó la organización), `connectable` y `reason` (por qué no se puede conectar). `has_next` sale de la cabecera `Link` de GitHub. |
| POST | `/github/repositories` | Body `{"full_name": "owner/repo"}`. Valida el repo contra GitHub (permiso de lectura, privado solo si está habilitado, hasta 50 MB) y lo conecta a la organización del usuario. 201 si es nuevo, 200 si ya estaba. |

El primer escaneo se lanza con el endpoint existente del Módulo A, `POST /repositories/{id}/scans`.

**Errores** (sin 401, que el frontend interpreta como sesión vencida de Qubitor):

| Código | Cuándo |
|---|---|
| 409 | El usuario no tiene GitHub vinculado en Clerk, o el token venció. |
| 403 | GitHub no permite el acceso (scopes, SSO de la organización). |
| 404 | El repo no existe o la cuenta no lo ve. |
| 422 | Nombre inválido, sin permiso de lectura, privado no habilitado o más de 50 MB. |
| 429 | Se agotó la cuota de la API de GitHub. Trae la cabecera `Retry-After`. |
| 503 | Clerk o GitHub no responden, o falta `CLERK_SECRET_KEY`. |

## Clonado seguro (`app/worker/clone.py`)

- Solo URLs `https://github.com/<owner>/<repo>`, validadas con `fullmatch`.
- `git clone --depth 1 --single-branch --no-tags --no-recurse-submodules`, con `core.symlinks=false`, solo protocolo HTTPS y la URL después de `--`.
- Límite de 50 MB, medido mientras clona, y timeout de 120 s. El clon se borra siempre en el `finally` del job.
- Git recibe un **entorno mínimo**: no hereda `DATABASE_URL`, `REDIS_URL` ni otras credenciales del worker, e ignora la configuración global y del sistema para que ningún credential helper guarde el token.
- El token de un repo privado viaja como cabecera `Authorization` por `GIT_CONFIG_COUNT/KEY/VALUE` (Git 2.31+). No queda en la URL, en los argumentos del proceso ni en `.git/config`.

## Configuración

### Clerk

1. **User & Authentication → SSO connections → GitHub:** usar **credenciales propias** (Client ID y Secret de una OAuth App de GitHub). Con las credenciales compartidas de desarrollo, Clerk no permite leer el token.
2. **Scopes:** `read:user` y `public_repo`. Para repos privados, `repo`.
3. Copiar **API Keys → Secret key** a `CLERK_SECRET_KEY` en el servicio de la API en Render.

### GitHub (OAuth App)

GitHub → Settings → Developer settings → OAuth Apps → New OAuth App. La *Authorization callback URL* la indica Clerk en la configuración del proveedor.

### Variables de entorno (`backend/.env.example`)

| Variable | Servicio | Descripción |
|---|---|---|
| `CLERK_SECRET_KEY` | API (y worker si hay repos privados) | Clave secreta de la Backend API de Clerk. **Secreto.** |
| `CLERK_GITHUB_PROVIDER` | API y worker | Opcional. Por defecto se prueba `oauth_github` y después `github`. |
| `GITHUB_PRIVATE_REPOS` | API y worker | `true` para permitir conectar y clonar repos privados. Por defecto `false`. |

> **Repos privados y seguridad.** Habilitarlos requiere cargar `CLERK_SECRET_KEY` también en el scan-worker. Mientras el motor SAST siga ejecutando Bandit con `python -m` desde la carpeta del repo, un repo malicioso podría leer las variables del worker. Por eso `GITHUB_PRIVATE_REPOS` queda en `false` hasta que esa corrección esté mergeada.

## Base de datos

La migración `9c2f1a7d3b10_repos_privados_github` agrega a `repositories`:

- `is_private` (boolean, por defecto `false`);
- `connected_by_user_id` (FK a `users`, `ON DELETE SET NULL`).

```bash
cd backend
alembic upgrade head
```

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
# Unitarios, sin red ni base:
python -m pytest tests/integrations tests/worker -q
# Endpoints y resolución del token contra un Postgres descartable:
QUBITOR_TEST_DATABASE_URL=postgresql+psycopg://postgres:qubitor@127.0.0.1:55432/qubitor_test python -m pytest tests/integrations -q
# Clonado real contra GitHub:
QUBITOR_TESTS_RED=1 python -m pytest tests/worker/test_clone.py tests/worker/test_clone_credenciales.py -q
```

GitHub y Clerk se simulan en los tests: no hace falta ninguna credencial real.
