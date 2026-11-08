/** Marca de Qubitor: el recuadro de doble filete del cartel con una lupa. */
export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className={className}>
      <rect x="1.5" y="1.5" width="29" height="29" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <rect x="4.5" y="4.5" width="23" height="23" rx="1" stroke="currentColor" strokeWidth="1" opacity="0.7" />
      <circle cx="15" cy="15" r="5.25" stroke="currentColor" strokeWidth="2" />
      <path d="M19 19l4 4" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" />
    </svg>
  )
}
