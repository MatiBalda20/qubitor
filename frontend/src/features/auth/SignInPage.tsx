import { SignedIn, useSignIn } from '@clerk/clerk-react'
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Logo } from '@/components/layout/Logo'
import { AUTH_ENABLED } from '@/lib/config'
import { GitHubIcon } from './GitHubIcon'

export default function SignInPage() {
  return (
    <main className="grid min-h-dvh place-items-center bg-paper px-4 py-12">
      <section
        aria-labelledby="sign-in-title"
        className="w-full max-w-sm rounded-sm bg-sheet shadow-sheet ring-1 ring-rule"
      >
        <header className="flex items-center gap-3 rounded-t-sm bg-civic px-6 py-4 text-civic-ink">
          <Logo className="size-7" />
          <span className="font-display text-2xl font-semibold tracking-wide">Qubitor</span>
        </header>
        <div className="space-y-5 px-6 py-7">
          <div className="space-y-1.5">
            <h1 id="sign-in-title" className="text-xl font-semibold text-ink">
              Ingresá a tu auditoría
            </h1>
            <p className="text-sm text-ink-2">
              Usamos tu cuenta de GitHub para leer los repositorios que elijas escanear.
            </p>
          </div>
          {AUTH_ENABLED ? <GitHubSignIn /> : <DemoNotice />}
        </div>
      </section>
    </main>
  )
}

function GitHubSignIn() {
  const { isLoaded, signIn } = useSignIn()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleClick() {
    if (!isLoaded) return
    setPending(true)
    setError(null)
    try {
      await signIn.authenticateWithRedirect({
        strategy: 'oauth_github',
        redirectUrl: '/sso-callback',
        redirectUrlComplete: '/',
      })
    } catch {
      setPending(false)
      setError('No pudimos abrir GitHub. Intentá de nuevo en unos segundos.')
    }
  }

  return (
    <>
      <SignedIn>
        <Navigate to="/" replace />
      </SignedIn>
      <button
        type="button"
        onClick={handleClick}
        disabled={!isLoaded || pending}
        className="flex h-11 w-full items-center justify-center gap-2.5 rounded-sm bg-ink font-semibold text-white transition-[background-color,scale] duration-150 hover:bg-civic-deep active:scale-[0.96] disabled:cursor-wait disabled:opacity-70"
      >
        <GitHubIcon className="size-5" />
        {pending ? 'Abriendo GitHub…' : 'Continuar con GitHub'}
      </button>
      {error && (
        <p role="alert" className="text-sm text-sev-critical">
          {error}
        </p>
      )}
    </>
  )
}

function DemoNotice() {
  return (
    <div className="space-y-4">
      <p className="rounded-sm bg-civic-soft px-3.5 py-3 text-sm text-ink-2">
        El login está desactivado porque falta <code className="font-mono text-[0.8125rem]">VITE_CLERK_PUBLISHABLE_KEY</code>.
        Podés recorrer la app con datos de ejemplo.
      </p>
      <Link
        to="/"
        className="flex h-11 w-full items-center justify-center rounded-sm bg-civic font-semibold text-civic-ink transition-[background-color,scale] duration-150 hover:bg-civic-deep active:scale-[0.96]"
      >
        Entrar en modo demo
      </Link>
    </div>
  )
}
