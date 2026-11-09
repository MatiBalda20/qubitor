/** Respuesta de GET /github/repositories (backend/app/integrations/github/routes.py). */
export interface GitHubRepo {
  /** ej. "qubitor-org/qubitor-demo-vulnerable" */
  full_name: string
  url: string
  private: boolean
  description: string | null
  default_branch: string
  size_bytes: number
  updated_at: string | null
  archived: boolean
  /** Ya lo conectó la organización. */
  connected: boolean
  /** Si se puede conectar; si no, `reason` dice por qué. */
  connectable: boolean
  reason: string | null
}

export interface GitHubRepoPage {
  items: GitHubRepo[]
  page: number
  has_next: boolean
}
