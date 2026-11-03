const env = import.meta.env

/** URL base de la API, sin barra final. */
export const API_URL = (env.VITE_API_URL ?? '').replace(/\/+$/, '')

/** Usa los mock.json de cada feature mientras el backend no esté listo. */
export const USE_MOCKS = env.VITE_USE_MOCKS === 'true' || API_URL === ''

export const CLERK_PUBLISHABLE_KEY = env.VITE_CLERK_PUBLISHABLE_KEY ?? ''

/** Sin clave de Clerk la app corre en modo demo, sin login. */
export const AUTH_ENABLED = CLERK_PUBLISHABLE_KEY !== ''
