import type { Socket } from 'socket.io-client'

export interface SshConsoleEvents {
  data: (data: string) => void
  error: (message: string) => void
  closed: () => void
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function listenSshConsole(
  socket: Socket,
  events: SshConsoleEvents
): () => void {
  const onData = (payload: unknown) => {
    if (isRecord(payload) && typeof payload.data === 'string') {
      events.data(payload.data)
    }
  }
  const onError = (payload: unknown) => {
    const message = isRecord(payload) && typeof payload.error === 'string'
      ? payload.error
      : 'The SSH terminal connection was interrupted.'
    events.error(message)
  }
  const onClosed = () => events.closed()

  socket.on('terminal:data', onData)
  socket.on('terminal:error', onError)
  socket.on('terminal:closed', onClosed)
  return () => {
    socket.off('terminal:data', onData)
    socket.off('terminal:error', onError)
    socket.off('terminal:closed', onClosed)
  }
}

export function sendSshConsoleInput(socket: Socket, data: string): void {
  if (socket.connected) {
    socket.emit('terminal:input', { data })
  }
}

export function resizeSshConsole(
  socket: Socket,
  columns: number,
  rows: number
): void {
  if (socket.connected) {
    socket.emit('terminal:resize', { columns, rows })
  }
}
