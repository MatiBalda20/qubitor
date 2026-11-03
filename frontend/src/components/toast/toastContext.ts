import { createContext, useContext } from 'react'

export interface ToastOptions {
  message: string
  /** Acción opcional, por ejemplo "Deshacer". */
  action?: { label: string; onClick: () => void }
  tone?: 'neutral' | 'error'
}

export const ToastContext = createContext<((toast: ToastOptions) => void) | null>(null)

/** Muestra un aviso breve al pie de la pantalla. */
export function useToast() {
  const show = useContext(ToastContext)
  if (!show) throw new Error('useToast debe usarse dentro de <ToastProvider>')
  return show
}
