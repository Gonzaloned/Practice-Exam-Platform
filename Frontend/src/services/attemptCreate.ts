import { requestAttemptApi } from './attemptApi'
import {
  ExamSessionError,
  isRecord,
  normalizeAttempt,
  type ExamSession,
} from './attemptTypes'
import { createAttemptEnvironment } from './vmEnvironment'

export async function createAttempt(examId: number): Promise<ExamSession> {
  const data = await requestAttemptApi(`/exams/${examId}/attempts`, 'POST')
  if (!isRecord(data) || !('attempt' in data)) {
    throw new ExamSessionError('The attempt service returned invalid data.', 0)
  }
  return normalizeAttempt(data.attempt)
}

export async function createAttemptForExam(
  examSlug: string
): Promise<ExamSession> {
  const examResponse = await requestAttemptApi(
    `/exams/by-slug/${encodeURIComponent(examSlug)}`
  )
  if (
    !isRecord(examResponse) ||
    !isRecord(examResponse.exam) ||
    typeof examResponse.exam.id !== 'number'
  ) {
    throw new ExamSessionError('The exam definition could not be found.', 0)
  }

  const attempt = await createAttempt(examResponse.exam.id)
  return createAttemptEnvironment(attempt.id)
}
