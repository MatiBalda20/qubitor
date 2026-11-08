import { Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { Logo } from './Logo'
import { Sidebar } from './Sidebar'

/** Layout principal: menú lateral fijo en escritorio y cajón en mobile. */
export function AppLayout() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { pathname } = useLocation()

  // El cajón se cierra al cambiar de ruta (incluido el botón "atrás").
  useEffect(() => setDrawerOpen(false), [pathname])

  useEffect(() => {
    if (!drawerOpen) return
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && setDrawerOpen(false)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [drawerOpen])

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[15.5rem_1fr]">
      <a
        href="#contenido"
        className="sr-only z-50 rounded-sm bg-sheet px-3 py-2 text-sm font-semibold text-civic focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Saltar al contenido
      </a>

      <aside className="sticky top-0 hidden h-dvh lg:block">
        <Sidebar />
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between bg-civic px-4 text-civic-ink lg:hidden">
        <div className="flex items-center gap-2">
          <Logo className="size-6" />
          <span className="font-display text-xl font-semibold tracking-wide">Qubitor</span>
        </div>
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-label="Abrir menú"
          aria-expanded={drawerOpen}
          aria-controls="menu-movil"
          className="-mr-2 grid size-11 place-items-center rounded-sm hover:bg-white/10"
        >
          <Menu className="size-5" aria-hidden="true" />
        </button>
      </header>

      <div
        className={cn(
          'fixed inset-0 z-40 lg:hidden',
          drawerOpen ? 'pointer-events-auto' : 'pointer-events-none',
        )}
        aria-hidden={!drawerOpen}
      >
        <div
          onClick={() => setDrawerOpen(false)}
          className={cn(
            'absolute inset-0 bg-ink/40 transition-opacity duration-300 ease-(--ease-swift)',
            drawerOpen ? 'opacity-100' : 'opacity-0',
          )}
        />
        <div
          id="menu-movil"
          role="dialog"
          aria-modal="true"
          aria-label="Menú"
          inert={!drawerOpen}
          className={cn(
            'absolute inset-y-0 left-0 w-[17rem] max-w-[85vw] shadow-float transition-transform duration-300 ease-(--ease-swift) motion-reduce:transition-none',
            drawerOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <Sidebar onNavigate={() => setDrawerOpen(false)} />
          <button
            type="button"
            onClick={() => setDrawerOpen(false)}
            aria-label="Cerrar menú"
            className="absolute top-2.5 right-2 grid size-11 place-items-center rounded-sm text-civic-ink hover:bg-white/10"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
      </div>

      <main id="contenido" className="min-w-0">
        <Outlet />
      </main>
    </div>
  )
}
