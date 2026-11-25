# Deploy en Render: staging y producción

La infraestructura de Render está definida como código en [`render.yaml`](../render.yaml) (Blueprint de Render). Define un proyecto, `qubitor`, con dos entornos separados.

| Entorno | Rama | Servicios en Render | Cuándo despliega |
|---|---|---|---|
| `staging` | `develop` | `qubitor-api-staging`, `qubitor-scan-worker-staging` | Cuando un commit de `develop` con la CI en verde llega al fork. |
| `production` | `main` | `qubitor-api`, `qubitor-scan-worker` | Cuando un commit de `main` con la CI en verde llega al fork. |

Flujo: `feature/*` → PR a `develop` → se prueba en staging → PR de `develop` a `main` → producción.

## Render despliega desde un fork

Render está conectado al fork [`MatiBalda20/qubitor`](https://github.com/MatiBalda20/qubitor), no a este repo. Para que un merge llegue solo a Render, el fork tiene un workflow de sincronización:

```
merge en ValentinaPertile/qubitor ──▶ CI en verde ──▶ sync (cada ~10 min) ──▶ fork ──▶ Render
```

- El workflow vive en la rama `sync` del fork, que es su rama por defecto (los workflows programados de GitHub solo corren desde ahí). `main` y `develop` del fork son copias exactas de las de este repo.
- Cada corrida mira el último commit de `main` y de `develop` acá y lo copia al fork **solo si los jobs de CI `Frontend (lint + build)` y `Backend (pytest)` pasaron en verde** para ese commit. Si la CI está en rojo o todavía corre, no copia nada y lo reintenta en la corrida siguiente.
- Solo avanza las ramas (fast-forward): nunca reescribe historia. **No se commitea nunca directo en `main` o `develop` del fork**; si pasa, el sync falla hasta que se corrija.
- Por eso los servicios usan `autoDeployTrigger: commit` y no `checksPass`: la CI ya se verificó acá, y los pushes que hace el sync no corren la CI del fork.
- Para no esperar al cron (GitHub puede atrasarlo varios minutos): fork → Actions → *Sync desde el repo del equipo* → *Run workflow*.
- Si un commit modifica archivos de `.github/workflows/`, GitHub no deja que el token del workflow lo copie y la corrida falla. Esa vez se sincroniza a mano con el botón *Sync fork* de la rama en el fork.

## Qué está en Render y qué no

- **En `render.yaml`:** la API (Python, `uvicorn app.main:app`) y el scan-worker (Docker, `backend/worker/Dockerfile`) de cada entorno, con su health check en `/health`. El scan-worker es un Web Service y no un Background Worker porque los workers de Render no tienen plan free.
- **Fuera de Render, uno por entorno:** la base (un proyecto de Supabase por entorno), la cola (una base de Upstash Redis por entorno) y el bucket de reportes. Staging nunca apunta a los de producción. La caché de OSV en Cloudflare KV se puede compartir porque guarda datos públicos.
- **En Cloudflare (no cambia):** el frontend, el webhook-worker y el keep-alive apuntan a producción. Staging no tiene frontend propio: se prueba con el frontend local (`VITE_API_URL` = URL de `qubitor-api-staging`), por eso su `CORS_ORIGINS` es `http://localhost:5173`. Staging no tiene keep-alive y se duerme tras 15 minutos sin tráfico.

## Plan y región

Todo en plan `free` y región `oregon`. Los cuatro Web Services comparten las 750 h/mes del workspace: el keep-alive mantiene despierta solo producción y staging duerme cuando no se usa. La región no se puede cambiar después de crear un servicio.

## Crear o sincronizar el Blueprint

1. Render → **New → Blueprint** → elegir este repo (rama `main`).
2. Revisar que los nombres de producción (`qubitor-api` y `qubitor-scan-worker`) coincidan con los servicios que ya existen. Si no coinciden, Render crea servicios nuevos con otra URL y hay que actualizar `VITE_API_URL` del frontend, `TARGETS` del keep-alive y `QUBITOR_API_URL` del webhook-worker.
3. Cargar los secretos que pide el panel (lista abajo).
4. Correr las migraciones contra la base de cada entorno: `alembic upgrade head` con el `DATABASE_URL` de ese entorno. El `preDeployCommand` de Render solo existe en planes pagos.

Render pide los valores `sync: false` **solo al crear el Blueprint**. Si después se agrega una variable así a `render.yaml`, hay que cargarla a mano en cada servicio.

## Secretos para cargar a mano en el panel

Cada entorno lleva sus propios valores. Qué es cada variable está explicado en [`backend/.env.example`](../backend/.env.example).

| Variable | API | Scan-worker | Notas |
|---|:-:|:-:|---|
| `DATABASE_URL` | ✓ | ✓ | Session pooler de Supabase del entorno, `postgresql+psycopg://…?sslmode=require`. |
| `REDIS_URL` | ✓ | ✓ | Upstash del entorno (`rediss://…`). Tiene que ser la misma en la API y el worker del mismo entorno. |
| `CLERK_ISSUER` | ✓ | | Instancia de Clerk del entorno (no es secreto, pero cambia por entorno). |
| `CLERK_SECRET_KEY` | ✓ | | |
| `INTERNAL_WEBHOOK_SECRET` | ✓ (solo producción) | | El mismo valor que el secreto del webhook-worker de Cloudflare. En staging lo genera Render. |
| `R2_ENDPOINT`, `R2_REGION` | ✓ | ✓ | Endpoint S3 y región de Supabase Storage. |
| `R2_BUCKET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | ✓ | ✓ | Bucket del entorno y sus credenciales. |
| `CF_ACCOUNT_ID`, `CF_KV_NAMESPACE_ID`, `CF_API_TOKEN` | | ✓ | Caché de OSV en Cloudflare KV. |
| `GEMINI_API_KEY` | | ✓ | Triage con IA. |

La configuración no secreta (`PYTHON_VERSION`, `CORS_ORIGINS`, `AUTH_DISABLED`, `GITHUB_PRIVATE_REPOS`, `SEMGREP_ENABLED`) está en los grupos `qubitor-staging-config` y `qubitor-production-config` de `render.yaml`.
