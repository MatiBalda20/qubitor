import { X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { ToastContext, type ToastOptions } from './toastContext'

const VISIBLE_MS = 5000
const CLOSE_MS = 250

/** Un toast a la vez, que sube desde abajo (receta toast de transitions.dev). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<(ToastOptions & { key: number }) | null>(null)
  const [open, setOpen] = useState(false)
  const hideTimer = useRef<number | undefined>(undefined)

  const close = useCallback(() => {
    window.clearTimeout(hideTimer.current)
    setOpen(false)
    hideTimer.current = window.setTimeout(() => setToast(null), CLOSE_MS)
  }, [])

  const show = useCallback(
    (options: ToastOptions) => {
      window.clearTimeout(hideTimer.current)
      setToast({ ...options, key: Date.now() })
      setOpen(false)
      // Un frame cerrado para que la transición de entrada se vea también al reemplazar.
      requestAnimationFrame(() => requestAnimationFrame(() => setOpen(true)))
      hideTimer.current = window.setTimeout(close, VISIBLE_MS)
    },
    [close],
  )

  useEffect(() => () => window.clearTimeout(hideTimer.current), [])

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center p-4 sm:justify-end sm:p-6">
        {toast && (
          <div
            key={toast.key}
            role={toast.tone === 'error' ? 'alert' : 'status'}
            className={cn(
              't-toast pointer-events-auto flex max-w-md items-center gap-3 rounded-sm py-2.5 pr-2 pl-4 text-sm text-white shadow-float',
              toast.tone === 'error' ? 'bg-sev-critical' : 'bg-ink',
              open && 'is-open',
            )}
            onMouseEnter={() => window.clearTimeout(hideTimer.current)}
            onMouseLeave={() => (hideTimer.current = window.setTimeout(close, VISIBLE_MS / 2))}
          >
            <span className="min-w-0 flex-1">{toast.message}</span>
            {toast.action && (
              <button
                type="button"
                onClick={() => {
                  toast.action?.onClick()
                  close()
                }}
                className="h-8 shrink-0 rounded-xs px-2.5 font-semibold text-civic-muted underline decoration-white/30 underline-offset-[3px] hover:text-white hover:decoration-white"
              >
                {toast.action.label}
              </button>
            )}
            <button
              type="button"
              onClick={close}
              aria-label="Cerrar aviso"
              className="grid size-8 shrink-0 place-items-center rounded-xs text-white/70 hover:bg-white/10 hover:text-white"
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    </ToastContext.Provider>
  )
}
