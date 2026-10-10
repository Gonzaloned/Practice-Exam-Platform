import { clearAccessToken } from './auth'
import { attemptIdPath, requestAttemptApi } from './attemptApi'
import {
  ExamSessionError,
  isRecord,
  normalizeAttempt,
  type ExamSession,
} from './attemptTypes'

export type {
  AttemptQuestion,
  ExamEnvironment,
  ExamSession,
  ExamVMInstance,
} from './attemptTypes'
export { ExamSessionError } from './attemptTypes'

function parseAttemptResponse(data: unknown): ExamSession {
  if (!isRecord(data) || !('attempt' in data)) {
    throw new ExamSessionError('The exam service returned an invalid attempt.', 0)
  }
  const attempt = normalizeAttempt(data.attempt)
  const cleanupErrors = isRecord(data) && Array.isArray(data.cleanup_errors)
    ? data.cleanup_errors.filter(
      (error): error is string => typeof error === 'string'
    )
    : []
  return {
    ...attempt,
    cleanup_error: cleanupErrors.length > 0
      ? cleanupErrors.join('; ')
      : undefined,
  }
}

export async function setAttemptData(
  attemptId: string | number
): Promise<ExamSession> {
  return parseAttemptResponse(
    await requestAttemptApi(attemptIdPath(attemptId))
  )
}

export async function finishAttemptData(
  attemptId: string | number
): Promise<ExamSession> {
  return parseAttemptResponse(
    await requestAttemptApi(`${attemptIdPath(attemptId)}/finish`, 'POST')
  )
}

export function expireLocalLogin(): void {
  clearAccessToken()
}
