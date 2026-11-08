import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react'
import { Loader } from '@/components/Loader'

/** Vuelta del OAuth de GitHub: Clerk termina el login y redirige al dashboard. */
export default function SsoCallbackPage() {
  return (
    <main className="grid min-h-dvh place-items-center bg-paper">
      <Loader label="Terminando el ingreso con GitHub…" />
      <AuthenticateWithRedirectCallback signInFallbackRedirectUrl="/" signUpFallbackRedirectUrl="/" />
    </main>
  )
}
