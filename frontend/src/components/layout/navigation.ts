import {
  Atom,
  FileCode2,
  FolderGit2,
  History,
  KeyRound,
  LayoutDashboard,
  Package,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

/** Menú lateral. Cada módulo suma acá la ruta de su vista. */
export const NAVIGATION: NavGroup[] = [
  {
    label: 'Resumen',
    items: [{ to: '/', label: 'Dashboard general', icon: LayoutDashboard }],
  },
  {
    label: 'Hallazgos',
    items: [
      { to: '/code', label: 'Código inseguro', icon: FileCode2 },
      { to: '/secrets', label: 'Secretos', icon: KeyRound },
      { to: '/pqc', label: 'Post-cuántica', icon: Atom },
      { to: '/dependencies', label: 'Dependencias', icon: Package },
    ],
  },
  {
    label: 'Repositorio',
    items: [
      { to: '/history', label: 'Historial', icon: History },
      { to: '/connect', label: 'Conectar repositorio', icon: FolderGit2 },
    ],
  },
]
