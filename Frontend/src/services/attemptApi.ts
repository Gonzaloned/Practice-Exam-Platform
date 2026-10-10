import { apiBaseUrl } from './auth'
import { ExamSessionError, isRecord } from './attemptTypes'

export type AttemptHttpMethod = 'GET' | 'POST' | 'DELETE'

export async function requestAttemptApi(
  path: string,
  method: AttemptHttpMethod = 'GET',
  body?: unknown
): Promise<unknown> {
  const token = localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token')
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (token) {
    headers.Authorization = ['Bearer', token].join(' ')
  }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/api${path}`, {
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
    throw new ExamSessionError(
      'The exam service returned an invalid response.',
      response.status
    )
  }
  if (!response.ok) {
    const message = isRecord(data) && typeof data.error === 'string'
      ? data.error
      : `The exam service request failed (${response.status}).`
    const code = isRecord(data) && typeof data.code === 'string'
      ? data.code
      : undefined
    throw new ExamSessionError(message, response.status, code)
  }
  return data
}

export function attemptIdPath(attemptId: string | number): string {
  return `/attempts/${encodeURIComponent(String(attemptId))}`
}
