import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { Logo } from './Logo'
import { NAVIGATION } from './navigation'
import { UserMenu } from './UserMenu'

interface SidebarProps {
  /** Se llama al navegar, para cerrar el cajón en mobile. */
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <div className="flex h-full flex-col bg-civic text-civic-ink">
      <div className="flex h-16 shrink-0 items-center gap-2.5 border-b border-white/12 px-5">
        <Logo className="size-7" />
        <span className="font-display text-[1.625rem] leading-none font-semibold tracking-wide">Qubitor</span>
      </div>

      <nav aria-label="Principal" className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {NAVIGATION.map((group) => (
          <div key={group.label}>
            <p className="px-2.5 pb-1.5 text-[0.6875rem] font-semibold tracking-[0.08em] text-civic-muted uppercase">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    end={to === '/'}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn(
                        'group relative flex h-10 items-center gap-3 rounded-sm px-2.5 text-sm transition-[background-color,color] duration-150',
                        isActive
                          ? 'bg-sheet font-semibold text-civic'
                          : 'text-civic-ink/85 hover:bg-white/8 hover:text-civic-ink',
                      )
                    }
                  >
                    <Icon className="size-[1.125rem] shrink-0" strokeWidth={1.75} aria-hidden="true" />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-white/12 p-3">
        <UserMenu />
      </div>
    </div>
  )
}
