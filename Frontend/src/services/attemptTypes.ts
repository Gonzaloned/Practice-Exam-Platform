export type VMStatus =
  | 'creating'
  | 'starting'
  | 'ready'
  | 'stopping'
  | 'deleting'
  | 'stopped'
  | 'failed'

export interface ExamEnvironment {
  id: number
  attempt_id: number
  provider: string
  node: string | null
  vm_id: number | null
  status: VMStatus
  created_at: string
  destroyed_at: string | null
}

export interface ExamVMInstance {
  id: number
  attempt_id: number
  requirement_id: number | null
  name: string
  vm_id: number | null
  status: VMStatus
  is_main: boolean
  created_at: string
  destroyed_at: string | null
}

export interface AttemptQuestion {
  id: number
  title: string
  description: string
  points: number
  order_index: number
}

export interface ExamSession {
  id: number
  exam_id: number
  exam_slug: string
  exam_name: string
  status: 'provisioning' | 'running' | 'completed' | 'expired' | 'failed'
  started_at: string
  expires_at: string
  finished_at: string | null
  questions: AttemptQuestion[]
  environment: ExamEnvironment | null
  vm_instances: ExamVMInstance[]
  cleanup_error?: string
  environment_error?: string
}

type AttemptPayload = Omit<ExamSession, 'environment' | 'cleanup_error'>

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

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isVMStatus(value: unknown): value is VMStatus {
  return (
    typeof value === 'string' &&
    ['creating', 'starting', 'ready', 'stopping', 'deleting', 'stopped', 'failed']
      .includes(value)
  )
}

function isExamVMInstance(value: unknown): value is ExamVMInstance {
  return (
    isRecord(value) &&
    typeof value.id === 'number' &&
    typeof value.attempt_id === 'number' &&
    (typeof value.requirement_id === 'number' || value.requirement_id === null) &&
    typeof value.name === 'string' &&
    (typeof value.vm_id === 'number' || value.vm_id === null) &&
    isVMStatus(value.status) &&
    typeof value.is_main === 'boolean' &&
    typeof value.created_at === 'string' &&
    (typeof value.destroyed_at === 'string' || value.destroyed_at === null)
  )
}

function isQuestion(value: unknown): value is AttemptQuestion {
  return (
    isRecord(value) &&
    typeof value.id === 'number' &&
    typeof value.title === 'string' &&
    typeof value.description === 'string' &&
    typeof value.points === 'number' &&
    typeof value.order_index === 'number'
  )
}

export function isExamAttempt(value: unknown): value is AttemptPayload {
  return (
    isRecord(value) &&
    typeof value.id === 'number' &&
    typeof value.exam_id === 'number' &&
    typeof value.exam_slug === 'string' &&
    typeof value.exam_name === 'string' &&
    ['provisioning', 'running', 'completed', 'expired', 'failed']
      .includes(String(value.status)) &&
    typeof value.started_at === 'string' &&
    typeof value.expires_at === 'string' &&
    (value.finished_at === null || typeof value.finished_at === 'string') &&
    Array.isArray(value.questions) &&
    value.questions.every(isQuestion) &&
    Array.isArray(value.vm_instances) &&
    value.vm_instances.every(isExamVMInstance)
  )
}

export function normalizeAttempt(value: unknown): ExamSession {
  if (!isExamAttempt(value)) {
    throw new ExamSessionError('The exam service returned an invalid attempt.', 0)
  }
  const mainVm = value.vm_instances.find(instance => instance.is_main)
  return {
    ...value,
    environment: mainVm
      ? {
        id: mainVm.id,
        attempt_id: mainVm.attempt_id,
        provider: 'proxmox',
        node: null,
        vm_id: mainVm.vm_id,
        status: mainVm.status,
        created_at: mainVm.created_at,
        destroyed_at: mainVm.destroyed_at,
      }
      : null,
  }
}
