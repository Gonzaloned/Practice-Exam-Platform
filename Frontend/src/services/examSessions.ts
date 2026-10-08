import { apiBaseUrl, clearAccessToken } from './auth'

export interface ExamEnvironment {
  id: number
  attempt_id: number
  provider: string
  node: string | null
  vm_id: number | null
  status: 'creating' | 'starting' | 'ready' | 'stopping' | 'deleting' | 'stopped' | 'failed'
  created_at: string
  destroyed_at: string | null
}

export interface ExamSession {
  id: number
  exam_id: number
  status: 'provisioning' | 'running' | 'completed' | 'expired' | 'failed'
  started_at: string
  expires_at: string
  finished_at: string | null
  environment: ExamEnvironment | null
  cleanup_error?: string
}

interface SessionResponse {
  session: ExamSession
  cleanup_error?: string
}

interface ErrorResponse {
  error?: string
  code?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isExamSession(value: unknown): value is ExamSession {
  if (
    !isRecord(value) ||
    typeof value.id !== 'number' ||
    typeof value.exam_id !== 'number' ||
    typeof value.started_at !== 'string' ||
    typeof value.expires_at !== 'string' ||
    (value.finished_at !== null && typeof value.finished_at !== 'string') ||
    !['provisioning', 'running', 'completed', 'expired', 'failed'].includes(
      String(value.status)
    )
  ) {
    return false
  }

  if (value.environment === null) {
    return true
  }

  return (
    isRecord(value.environment) &&
    typeof value.environment.id === 'number' &&
    typeof value.environment.attempt_id === 'number' &&
    typeof value.environment.provider === 'string' &&
    (typeof value.environment.node === 'string' || value.environment.node === null) &&
    (typeof value.environment.vm_id === 'number' || value.environment.vm_id === null) &&
    ['creating', 'starting', 'ready', 'stopping', 'deleting', 'stopped', 'failed'].includes(
      String(value.environment.status)
    ) &&
    typeof value.environment.created_at === 'string' &&
    (typeof value.environment.destroyed_at === 'string' ||
      value.environment.destroyed_at === null)
  )
}

export class ExamSessionError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string
  ) {
    super(message)
    this.name = 'ExamSessionError'
  }
}

async function requestSession(
  path: string,
  method: 'GET' | 'POST',
  body?: unknown
): Promise<SessionResponse> {
  const token = localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token')
  const headers: Record<string, string> = {
    Accept: 'application/json',
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/api/exam${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ExamSessionError(
      'Could not connect to the exam service. Check your connection and try again.',
      0
    )
  }

  let data: unknown
  try {
    data = await response.json()
  } catch {
    throw new ExamSessionError('The exam service returned an invalid response.', response.status)
  }

  if (!response.ok) {
    const errorData: ErrorResponse = isRecord(data) ? {
      error: typeof data.error === 'string' ? data.error : undefined,
      code: typeof data.code === 'string' ? data.code : undefined,
    } : {}
    throw new ExamSessionError(
      errorData.error || `The exam service request failed (${response.status}).`,
      response.status,
      errorData.code
    )
  }

  if (!isRecord(data) || !isExamSession(data.session)) {
    throw new ExamSessionError('The exam service returned an invalid session.', response.status)
  }

  return {
    session: data.session,
    cleanup_error: typeof data.cleanup_error === 'string'
      ? data.cleanup_error
      : undefined,
  }
}

export async function startExamSession(examSlug: string): Promise<ExamSession> {
  const { session } = await requestSession('/sessions', 'POST', {
    exam_slug: examSlug,
  })
  return session
}

export async function getExamSession(sessionId: string): Promise<ExamSession> {
  const response = await requestSession(`/sessions/${encodeURIComponent(sessionId)}`, 'GET')
  return {
    ...response.session,
    cleanup_error: response.cleanup_error,
  }
}

export async function finishExamSession(sessionId: string): Promise<ExamSession> {
  const response = await requestSession(
    `/sessions/${encodeURIComponent(sessionId)}/finish`,
    'POST'
  )
  return {
    ...response.session,
    cleanup_error: response.cleanup_error,
  }
}

export function expireLocalLogin(): void {
  clearAccessToken()
}
