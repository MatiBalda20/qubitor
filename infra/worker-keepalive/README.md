# qubitor-keepalive

Cloudflare Worker con Cron Trigger que hace `GET /health` cada 10 minutos a los
servicios de Render (plan free) para que no se apaguen por inactividad. Solo
corre de 8:00 a 22:59 hora de Argentina; el porqué del horario está explicado en
`wrangler.toml`.

- Las URLs están en `[vars] TARGETS` de `wrangler.toml`, separadas por coma y sin
  `/health`. Para sumar el scan-worker, agregá su URL ahí y volvé a desplegar.
- No usa secretos ni expone rutas HTTP (`workers_dev = false`).

## Desplegar

Desde esta carpeta:

```bash
npm install
npx wrangler login     # una sola vez, abre el navegador
npx wrangler deploy
```

El deploy muestra el cron registrado (`schedule: */10 0-1,11-23 * * *`).

## Probar en local

```bash
npx wrangler dev --test-scheduled
# en otra terminal:
curl "http://localhost:8787/__scheduled?cron=*/10+*+*+*+*"
```

La consola de `wrangler dev` muestra una línea `keepalive ok …` o
`keepalive fail …` por cada URL.

## Ver los logs

- En vivo: `npx wrangler tail` (o `npx wrangler tail --format pretty`).
- Historial: dashboard de Cloudflare → Workers & Pages → `qubitor-keepalive` →
  pestaña **Logs** (Workers Logs está activado con `[observability]`). La
  pestaña **Settings → Triggers** muestra las próximas ejecuciones del cron.

Cada línea trae `url`, `ok`, `status`, `ms` y, si falló, `error` (por ejemplo,
`timeout tras 30000 ms`).
