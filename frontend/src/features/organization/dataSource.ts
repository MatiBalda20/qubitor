import { request } from '@/lib/api'
import { USE_MOCKS } from '@/lib/config'
import mock from './mock.json'

export type MemberRole = 'admin' | 'member'

/** GET /me: quién es el usuario en la organización activa y qué puede hacer. */
export interface Me {
  user_id: string
  role: MemberRole
  organization: { id: string; name: string; personal: boolean }
  permissions: { connect_repositories: boolean; start_scans: boolean; update_findings: boolean }
}

/** GET /organization/members: miembros que ya usaron Qubitor. */
export interface Member {
  user_id: string
  name: string | null
  image_url: string | null
  role: MemberRole
  joined_at: string | null
  last_seen_at: string | null
  is_you: boolean
}

export interface OrganizationData {
  me: Me
  members: Member[]
}

const MOCK_LATENCY_MS = 350

export async function loadOrganization(): Promise<OrganizationData> {
  if (USE_MOCKS) {
    await new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS))
    return structuredClone({ me: mock.me as Me, members: mock.members as Member[] })
  }
  const [me, members] = await Promise.all([request<Me>('/me'), request<Member[]>('/organization/members')])
  return { me, members }
}
