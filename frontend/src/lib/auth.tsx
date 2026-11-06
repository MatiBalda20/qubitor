import { ClerkProvider, SignedIn, SignedOut, useAuth } from '@clerk/clerk-react'
import { useEffect, type ReactNode } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { setTokenGetter } from './api'
import { AUTH_ENABLED, CLERK_PUBLISHABLE_KEY } from './config'

/**
 * Autenticación con Clerk (proveedor GitHub). Sin VITE_CLERK_PUBLISHABLE_KEY
 * la app corre en modo demo: no hay login y las rutas quedan abiertas.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  if (!AUTH_ENABLED) return children

  return (
    <ClerkProvider
      publishableKey={CLERK_PUBLISHABLE_KEY}
      routerPush={(to) => navigate(to)}
      routerReplace={(to) => navigate(to, { replace: true })}
      signInUrl="/sign-in"
      afterSignOutUrl="/sign-in"
    >
      <TokenBridge />
      {children}
    </ClerkProvider>
  )
}

/** Conecta el JWT de Clerk con el cliente de la API. */
function TokenBridge() {
  const { getToken } = useAuth()
  useEffect(() => {
    setTokenGetter(() => getToken())
  }, [getToken])
  return null
}

/** Envuelve las rutas privadas: sin sesión, redirige al login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  if (!AUTH_ENABLED) return children
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" replace />
      </SignedOut>
    </>
  )
}
