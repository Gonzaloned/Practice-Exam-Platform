import { attemptIdPath, requestAttemptApi } from './attemptApi'
import {
  ExamSessionError,
  isRecord,
  normalizeAttempt,
  type ExamSession,
} from './attemptTypes'

function parseEnvironmentResponse(data: unknown): ExamSession {
  if (!isRecord(data) || !('attempt' in data)) {
    throw new ExamSessionError(
      'The environment service returned an invalid attempt.',
      0
    )
  }
  const attempt = normalizeAttempt(data.attempt)
  const cleanupErrors = Array.isArray(data.cleanup_errors)
    ? data.cleanup_errors.filter(
      (error): error is string => typeof error === 'string'
    )
    : []
  const environmentError = typeof data.error === 'string'
    ? data.error
    : undefined
  return {
    ...attempt,
    cleanup_error: cleanupErrors.length > 0
      ? cleanupErrors.join('; ')
      : undefined,
    environment_error: environmentError,
  }
}

export async function createAttemptEnvironment(
  attemptId: number
): Promise<ExamSession> {
  return parseEnvironmentResponse(
    await requestAttemptApi(`${attemptIdPath(attemptId)}/environment`, 'POST')
  )
}

export async function advanceAttemptEnvironment(
  attemptId: string | number
): Promise<ExamSession> {
  return parseEnvironmentResponse(
    await requestAttemptApi(`${attemptIdPath(attemptId)}/environment`)
  )
}

export async function cleanupAttemptEnvironment(
  attemptId: string | number
): Promise<ExamSession> {
  return parseEnvironmentResponse(
    await requestAttemptApi(`${attemptIdPath(attemptId)}/environment`, 'DELETE')
  )
}
