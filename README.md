# Rama `sync`

Rama por defecto de este fork. Solo contiene el workflow
[`sync-upstream.yml`](.github/workflows/sync-upstream.yml), que copia `main` y `develop`
de [ValentinaPertile/qubitor](https://github.com/ValentinaPertile/qubitor) a este fork
cuando la CI de ese commit pasó en verde. Render despliega desde `main` (producción) y
`develop` (staging) de este fork.

- No commitear directo en `main` ni en `develop` de este fork: el sync solo avanza las ramas.
- Para sincronizar sin esperar al cron: Actions → *Sync desde el repo del equipo* → *Run workflow*.

Más detalle en `docs/deploy.md` del repo del equipo.
