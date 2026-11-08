# Módulo E — Pantalla «Conectar repositorio»

`frontend/src/features/connect/`, en la ruta `/connect` («Conectar repositorio» en el menú lateral).

## Qué hace

- Lista los repos de la cuenta de GitHub del usuario (`GET /github/repositories`) con rama por defecto, tamaño, última actualización y si son privados o archivados.
- Si un repo no se puede conectar, muestra el motivo que manda el backend: privados no habilitados, más de 50 MB o sin permiso.
- **Búsqueda** por nombre y descripción entre los repos cargados, sin distinguir mayúsculas ni tildes.
- **Paginación:** «Cargar más» pide la página siguiente mientras `has_next` sea `true`.
- **Conectar y escanear:** `POST /github/repositories` y después `POST /repositories/{id}/scans` (Módulo A). El progreso se muestra con `ScanProgress` y `useScanPolling`, y al terminar ofrece ir al dashboard.
- **Repo público por URL:** valida la URL con la misma regla que el backend antes de enviarla (`POST /repositories`).
- **Estados:** carga (`Skeleton`), error (`EmptyState` con «Reintentar»; si el backend responde 409, explica que la cuenta de GitHub no está vinculada), vacío y datos.

El token de GitHub nunca llega al navegador: el frontend solo manda el JWT de Clerk y el backend pide el token a Clerk.

## Archivos

| Archivo | Contenido |
|---|---|
| `ConnectPage.tsx` | La vista, con la fila de repo y el formulario de URL. |
| `dataSource.ts` | API real o `mock.json` según `USE_MOCKS`, como las demás vistas. |
| `search.ts` | Búsqueda, orden, validación de la URL y formato del tamaño. |
| `types.ts` | Tipos de la respuesta de `/github/repositories`. |
| `mock.json` | Dos páginas de ejemplo: repos conectados, privados, archivados y de más de 50 MB. |

## Cambios fuera de `features/connect/`

Para revisión del Módulo B:

- `lib/api.ts`: se exporta `request`, para que cada módulo declare sus endpoints en su carpeta. No cambia el comportamiento.
- `App.tsx`: se reemplaza el `ModulePlaceholder` de `/connect`.
- **Tests del frontend:** no existían. Se sumaron Vitest, jsdom y Testing Library (solo `devDependencies`), con `vitest.config.ts`, `src/test/setup.ts` y el script `npm test`. Los tests usan siempre los mocks.

## Probar

```bash
cd frontend
npm install
npm test          # búsqueda, validación, paginación, conexión, errores (también 409)
npm run lint && npm run build
VITE_USE_MOCKS=true npm run dev   # http://localhost:5173/connect con datos de ejemplo
```
