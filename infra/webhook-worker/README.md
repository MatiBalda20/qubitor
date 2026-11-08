# Worker de webhooks de GitHub (Módulo E)

Cloudflare Worker que recibe los webhooks de GitHub y le pide a la API de Qubitor un escaneo en cada push a la rama por defecto. Es el equivalente a AWS Lambda + API Gateway: no hay un servidor propio esperando los eventos.

```
GitHub ──push──▶ Worker ──POST /internal/github/push (HMAC)──▶ API (Render) ──RQ──▶ scan-worker
          firma X-Hub-Signature-256              firma X-Qubitor-Signature
```

## Qué hace

1. Lee el cuerpo con un tope de 2 MiB, sin cargar más de eso en memoria.
2. **Verifica la firma de GitHub** (`X-Hub-Signature-256`, HMAC-SHA256 con `GITHUB_WEBHOOK_SECRET`) antes de mirar cualquier otro dato. Usa `crypto.subtle.verify`, que compara en tiempo constante.
3. Responde `ping` con 200. Ignora con 202 los eventos que no son `push`, los push a otras ramas y los borrados de rama.
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
npm test            # vitest: firma, eventos, duplicados, API caída, tamaño del cuerpo
npm run typecheck   # tsc --noEmit
npm run types       # regenera worker-configuration.d.ts si cambian los bindings
```

Los tipos de `Env` se generan con `wrangler types --include-runtime=false` a partir de `wrangler.jsonc`. Los del runtime vienen de `@cloudflare/workers-types`.

## Despliegue (pendiente, no se hizo)

1. `npx wrangler kv namespace create DELIVERIES` y copiar el id en `wrangler.jsonc`.
2. `npx wrangler secret put GITHUB_WEBHOOK_SECRET` y `npx wrangler secret put INTERNAL_WEBHOOK_SECRET`.
3. Cargar `INTERNAL_WEBHOOK_SECRET` en el servicio de la API en Render.
4. `npx wrangler deploy`.
5. En GitHub, en cada repo (o en la organización) → Settings → Webhooks → Add webhook:
   - *Payload URL* `https://<worker>.workers.dev/github/webhook`;
   - *Content type* `application/json`;
   - *Secret* = `GITHUB_WEBHOOK_SECRET`;
   - solo el evento *push*.
