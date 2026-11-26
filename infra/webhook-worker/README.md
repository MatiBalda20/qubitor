# Worker de webhooks de GitHub (Módulo E)

Cloudflare Worker que recibe los webhooks de GitHub y le pide a la API de Qubitor un escaneo en cada push a la rama por defecto. Es el equivalente a AWS Lambda + API Gateway: no hay un servidor propio esperando los eventos.

```
GitHub ──push──▶ Worker ──POST /internal/github/push (HMAC)──▶ API (Render) ──RQ──▶ scan-worker
          firma X-Hub-Signature-256              firma X-Qubitor-Signature
```

## Qué hace

1. Lee el cuerpo con un tope de 2 MiB, sin cargar más de eso en memoria.
2. **Verifica la firma de GitHub** (`X-Hub-Signature-256`, HMAC-SHA256 con `GITHUB_WEBHOOK_SECRET`) antes de mirar cualquier otro dato. Usa `crypto.subtle.verify`, que compara en tiempo constante.
3. Responde `ping` con 200. Ignora con 202 los eventos que no son `push`, los push a otras ramas, los borrados de rama y los repos que no están en `ALLOWED_REPOSITORIES`.
4. Descarta las **entregas repetidas** (`X-GitHub-Delivery`) con Workers KV durante 24 h. La API también deduplica por el id de entrega, porque KV es eventualmente consistente.
5. Reenvía a la API **solo** el repo, el commit, la rama y el id de entrega, firmados con HMAC-SHA256 sobre `"<timestamp>.<cuerpo>"` con `INTERNAL_WEBHOOK_SECRET`. La API rechaza firmas de más de 5 minutos.
6. Marca la entrega en KV recién cuando la API aceptó. Si la API falla, responde 502 y la entrega se puede reenviar desde GitHub.

**El Worker no tiene acceso a Redis.** La cola de escaneos (Upstash Redis + RQ) sigue siendo del Módulo A y solo la usa la API: con `REDIS_URL` se puede ejecutar código en el scan-worker, así que no se reparte esa credencial.

Logs estructurados en JSON (Workers Logs y Traces habilitados en `wrangler.jsonc`), sin secretos ni el contenido del evento.

## Configuración

| Nombre | Tipo | Dónde | Descripción |
|---|---|---|---|
| `GITHUB_WEBHOOK_SECRET` | secreto | Worker | El mismo valor que el *Secret* del webhook en GitHub. |
| `INTERNAL_WEBHOOK_SECRET` | secreto | Worker **y** API | Secreto compartido entre el Worker y la API, de 32 caracteres o más. Generarlo con `openssl rand -hex 32`. |
| `QUBITOR_API_URL` | variable | `wrangler.jsonc` | URL pública de la API en Render, sin barra final. |
| `DELIVERIES` | KV | `wrangler.jsonc` | Namespace para las entregas procesadas. |
| `ALLOWED_REPOSITORIES` | variable | `wrangler.jsonc` | Repos (`owner/repo`, separados por comas) que pueden disparar escaneos. Vacía, no se acepta ninguno. Ver «Limitación de seguridad». |

## Ejecución local

```bash
cd infra/webhook-worker
npm install
cp .dev.vars.example .dev.vars   # completar los dos secretos (.dev.vars no se commitea)
npm run dev                      # wrangler dev en http://localhost:8787/github/webhook
```

En `.dev.vars` se puede apuntar `QUBITOR_API_URL` a la API local (`QUBITOR_API_URL=http://localhost:8000`), que tiene que tener el mismo `INTERNAL_WEBHOOK_SECRET`.

Para mandar un evento firmado a mano:

```bash
BODY='{"ref":"refs/heads/main","after":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","repository":{"html_url":"https://github.com/acme/demo","default_branch":"main"}}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$GITHUB_WEBHOOK_SECRET" | sed 's/^.* //')
curl -X POST http://localhost:8787/github/webhook \
  -H "X-GitHub-Event: push" -H "X-GitHub-Delivery: 72d3162e-cc78-11e3-81ab-4c9367dc0958" \
  -H "X-Hub-Signature-256: sha256=$SIG" -H "Content-Type: application/json" -d "$BODY"
```

## Tests y tipos

```bash
npm test            # vitest: firma, eventos, duplicados, repos autorizados, API caída, tamaño del cuerpo
npm run typecheck   # tsc --noEmit
npm run types       # regenera worker-configuration.d.ts si cambian los bindings
```

Los tipos de `Env` se generan con `wrangler types --include-runtime=false` a partir de `wrangler.jsonc`. Los del runtime vienen de `@cloudflare/workers-types`.

## Despliegue (pendiente: no se hizo todavía)

Al 26/11/2026 el Worker **no está desplegado** en Cloudflare y el webhook de GitHub no está configurado. El código está probado de punta a punta en local con `wrangler dev` (evento firmado → Worker → API → Redis/RQ → scan-worker → escaneo `completed`). Lo tiene que desplegar quien tenga acceso a la cuenta de Cloudflare (`scanner-app`) y a Render.

Orden recomendado (cada paso se verifica antes del siguiente):

1. **Mergear a `main`** el PR que trae este README, por el flujo `feature/*` → `develop` → `main` de [CONTRIBUTING](../../docs/CONTRIBUTING.md). No desplegar desde una rama sin mergear.
2. **Cuenta correcta:** `npx wrangler login` y `npx wrangler whoami`: tiene que ser la cuenta del subdominio `scanner-app.workers.dev` (la del frontend).
3. **KV:** `npx wrangler kv namespace list`. Si ya existe uno para este Worker (por ejemplo `qubitor-webhook-worker-DELIVERIES` o `DELIVERIES`), reusarlo. Si no, `npx wrangler kv namespace create DELIVERIES`. Copiar el `id` en `wrangler.jsonc` en lugar de `reemplazar-por-el-id-del-namespace` y subirlo **por PR** (el id no es un secreto).
4. **`INTERNAL_WEBHOOK_SECRET`** tiene que ser **el mismo** en la API de producción de Render y en el Worker:
   - Si la API de Render ya lo tiene cargado y alguien conoce el valor (por ejemplo, está en el gestor de contraseñas del equipo), usar ese valor.
   - Si no se conoce (Render no muestra el valor) o no existe, generar uno nuevo (`openssl rand -hex 32`), cargarlo en Render → `qubitor-api` → *Environment* (reemplaza el anterior y redespliega la API) y usar el mismo en el Worker.
   - En el Worker: `npx wrangler secret put INTERNAL_WEBHOOK_SECRET` (lo pide por teclado; no pasarlo como argumento ni dejarlo en el historial de la terminal).
5. **`GITHUB_WEBHOOK_SECRET`:** otro valor distinto (`openssl rand -hex 32`) y `npx wrangler secret put GITHUB_WEBHOOK_SECRET`. Guardarlo para el paso 8.
6. **`ALLOWED_REPOSITORIES`** en `wrangler.jsonc`: hoy solo `ValentinaPertile/qubitor-demo-vulnerable`. Agregar otro repo es una decisión del equipo, por PR (ver «Limitación de seguridad»).
7. **Desplegar** desde `main` actualizado: `npm ci && npm test && npm run typecheck && npx wrangler deploy`. Anotar la URL que imprime Wrangler. Comprobar: `curl -i -X POST https://<url>/github/webhook` responde **401** (sin firma) y `curl -i https://<url>/github/webhook` responde **405**.
8. **GitHub:** en `qubitor-demo-vulnerable` → Settings → Webhooks. Si ya hay uno con esa URL, editarlo en lugar de crear otro. *Add webhook*:
   - *Payload URL*: `https://<url real del paso 7>/github/webhook`;
   - *Content type*: `application/json`;
   - *Secret*: el valor del paso 5;
   - *Which events*: **Just the push event**.

   GitHub manda un `ping`: en *Recent Deliveries* tiene que verse **200**.
9. **Prueba real:** un push a la rama por defecto del repo de demo (un cambio controlado, sin tocar los archivos con vulnerabilidades plantadas) o *Redeliver* de una entrega de push. Verificar:
   - en *Recent Deliveries*, respuesta **202** con `"accepted": true` y un id en `scans`;
   - `npx wrangler tail` muestra `outcome: escaneo_pedido`;
   - en los logs de Render de la API, `POST /internal/github/push 202`; en los del scan-worker, `Successfully completed app.worker.job.run_scan(...)`;
   - el escaneo aparece en el historial de la app con el commit del push. Si la API responde 401, los `INTERNAL_WEBHOOK_SECRET` no coinciden; si responde 503, falta en Render.

   La API tiene que estar despierta (keep-alive de 9 a 21 h, hora de Argentina): fuera de ese horario el primer pedido puede tardar ~1 minuto y el Worker corta a los 10 s con 502. En ese caso, *Redeliver* desde GitHub cuando la API ya respondió `/health`.

## Limitación de seguridad (QUB-07)

`GITHUB_WEBHOOK_SECRET` es **uno solo** para todos los webhooks. Si cada cliente configurara su webhook con ese valor, cualquiera de ellos podría firmar eventos `push` de repos ajenos. Mitigaciones actuales:

- el Worker solo acepta los repos de `ALLOWED_REPOSITORIES` (los demás se ignoran con 202 sin llegar a la API);
- la API aplica a los escaneos del webhook el mismo límite de escaneos simultáneos por organización que al escaneo manual.

Con esto el webhook sirve para el repo de demo del equipo, pero **no es apto para varios clientes**. La solución es un secreto por repositorio u organización, guardado en la base y verificado por la API (el Worker reenviaría el cuerpo y la firma de GitHub), o una GitHub App con su propio secreto.
