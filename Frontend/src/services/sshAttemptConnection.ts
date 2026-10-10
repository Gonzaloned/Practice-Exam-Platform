import { io, type Socket } from 'socket.io-client'
import { apiBaseUrl } from './auth'

export interface TerminalAck {
  ok: boolean
  error?: string
  attempt_id?: number
  vm_instance_id?: number
  vm_name?: string
}

function isTerminalAck(value: unknown): value is TerminalAck {
  return (
    typeof value === 'object' &&
    value !== null &&
    'ok' in value &&
    typeof value.ok === 'boolean' &&
    (!('error' in value) || typeof value.error === 'string') &&
    (!('attempt_id' in value) || typeof value.attempt_id === 'number') &&
    (!('vm_instance_id' in value) || typeof value.vm_instance_id === 'number') &&
    (!('vm_name' in value) || typeof value.vm_name === 'string')
  )
}

export function createAttemptSshConnection(token: string): Socket {
  return io(`${apiBaseUrl}/terminal`, {
    autoConnect: false,
    auth: { token },
  })
}

export async function connectAttemptSsh(
  socket: Socket,
  attemptId: number
): Promise<TerminalAck> {
  if (!socket.connected) {
    throw new Error('The terminal service is not connected.')
  }
  const response: unknown = await socket
    .timeout(15_000)
    .emitWithAck('terminal:connect', { attempt_id: attemptId })
  if (!isTerminalAck(response)) {
    throw new Error('The terminal service returned an invalid response.')
  }
  if (!response.ok) {
    throw new Error(response.error || 'The terminal request failed.')
  }
  return response
}
