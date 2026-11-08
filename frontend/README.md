# Qubitor — Frontend

SPA en React + Vite + TypeScript + Tailwind CSS. Es la base compartida del Módulo B: layout, login, cliente de la API, tipos, componentes comunes y el Dashboard general. Cada módulo construye sus vistas encima, en `src/features/<módulo>/`.

## Correr en local

```bash
cd frontend
npm install
cp .env.example .env
npm run dev          # http://localhost:5173
```

Sin cambiar nada, la app arranca en **modo demo**: sin login y con los datos de `src/features/dashboard/mock.json`.

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo |
| `npm run build` | Type-check (`tsc -b`) y build de producción en `dist/` |
| `npm run lint` | ESLint |
| `npm run preview` | Sirve el build de producción |

## Variables de entorno

| Variable | Para qué |
|---|---|
| `VITE_API_URL` | URL de la API FastAPI. Vacía = se usan los mocks. |
| `VITE_USE_MOCKS` | `true` fuerza los mocks aunque haya API. |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clave pública de Clerk. Vacía = modo demo sin login. |

### Activar el login con Clerk

1. Crear una cuenta en [clerk.com](https://clerk.com) y una aplicación nueva.
2. En **Configure → SSO connections**, activar **GitHub** (y desactivar email si solo queremos GitHub).
3. En **API keys**, copiar la **Publishable key** (`pk_test_…`) en `VITE_CLERK_PUBLISHABLE_KEY` del `.env`.
4. Reiniciar `npm run dev`. Las rutas privadas redirigen a `/sign-in`.

La publishable key es pública por diseño (va en el bundle). La **secret key** (`sk_…`) es solo del backend y nunca va en el frontend.

## Estructura

```
src/
├── components/          # base compartida (Módulo B). Cambios: PR revisado por B
│   ├── layout/          # AppLayout, Sidebar, PageHeader, navegación
│   ├── toast/           # ToastProvider + useToast
│   ├── SeverityBadge, FindingCard, FindingsTable, CodeSnippet,
│   ├── EmptyState, Loader (y Skeleton), ScanProgress,
│   └── StatusStamp, FindingStatusActions
├── hooks/useScanPolling.ts   # polling a /scans/{id}
├── lib/
│   ├── api.ts           # cliente unificado de la API (JWT de Clerk incluido)
│   ├── auth.tsx         # Clerk + modo demo
│   ├── risk.ts          # pesos, Risk Score y nota A–F (plan, sección 5)
│   └── labels.ts, format.ts, config.ts, …
├── types/               # Finding.ts copia el contrato de engines/base.py
└── features/
    ├── auth/            # login con GitHub (Módulo B)
    └── dashboard/       # Dashboard general + mock.json (Módulo B)
```

## Cómo sumar la vista de un módulo

1. Crear `src/features/<módulo>/` con tu página y tu `mock.json` (formato de `types/Finding.ts`).
2. En `src/App.tsx`, reemplazar el `ModulePlaceholder` de tu ruta por tu página.
3. Usar los componentes comunes en vez de rehacerlos: `FindingsTable` ya trae filtros, detalle expandible y acciones de estado.
4. Pedir datos con `api` de `lib/api.ts`; mientras no haya backend, leer tu `mock.json` cuando `USE_MOCKS` sea `true`.

La guía visual (tokens, tipografías, componentes) está en [`DESIGN.md`](../DESIGN.md).

## Pendiente de acordar con el Módulo A

Los tipos de `Scan`, `Repository` y los campos que la API agrega a `Finding` (`id`, `status`, `fingerprint`, `triage`) son provisorios: siguen `docs/ARCHITECTURE.md` y el plan. Cuando el backend publique sus modelos, se ajustan en `src/types/`. Endpoints que usa el dashboard: `GET /repositories`, `GET /repositories/{id}/history`, `POST /repositories/{id}/scans`, `GET /scans/{id}`, `GET /scans/{id}/findings` y `PATCH /findings/{id}` con `{ "status": "open" | "resolved" | "false_positive" }`.
