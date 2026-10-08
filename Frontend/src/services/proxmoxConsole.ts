import { io, type Socket } from 'socket.io-client'
import { apiBaseUrl } from './auth'

export interface ProxmoxVm {
  vmid: number
  name?: string
  status?: string
  uptime?: number
}

export type ProxmoxConsoleCommand = 'connect' | 'vms' | 'status' | 'start' | 'stop'

export interface ProxmoxCommandResponse {
  ok: boolean
  status: number
  error?: string
  message?: string
  task_id?: string | null
  node?: string
  connected?: boolean
  version?: {
    version?: string
    release?: string
    repository?: string
  }
  vms?: ProxmoxVm[]
  vm?: ProxmoxVm
}

export class ProxmoxConsoleError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'ProxmoxConsoleError'
  }
}

export function createProxmoxSocket(token: string): Socket {
  return io(`${apiBaseUrl}/proxmox`, {
    autoConnect: false,
    auth: { token },
  })
}

export async function sendProxmoxCommand(
  socket: Socket,
  command: ProxmoxConsoleCommand,
  vmid?: number
): Promise<ProxmoxCommandResponse> {
  if (!socket.connected) {
    throw new ProxmoxConsoleError(
      'The Flask Socket.IO connection is not available.',
      0
    )
  }

  let response: unknown
  try {
    response = await socket
      .timeout(30_000)
      .emitWithAck('proxmox:command', { command, vmid })
  } catch {
    throw new ProxmoxConsoleError(
      'Flask did not acknowledge the Proxmox command before it timed out.',
      0
    )
  }

  if (
    typeof response !== 'object' ||
    response === null ||
    typeof (response as ProxmoxCommandResponse).ok !== 'boolean' ||
    typeof (response as ProxmoxCommandResponse).status !== 'number'
  ) {
    throw new ProxmoxConsoleError(
      'Flask returned an invalid Socket.IO response.',
      0
    )
  }

  const result = response as ProxmoxCommandResponse
  if (!result.ok) {
    throw new ProxmoxConsoleError(
      result.error || `The Proxmox command failed (${result.status}).`,
      result.status
    )
  }
  return result
}
