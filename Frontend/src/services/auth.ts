export interface AuthUser {
  id: number
  full_name: string
  email: string
  created_at: string
}

interface AuthResponse {
  message: string
  user: AuthUser
  access_token?: string
}

interface RegisterDetails {
  full_name: string
  email: string
  password: string
}

interface LoginDetails {
  email: string
  password: string
}

export const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'
).replace(/\/+$/, '')

export function hasAccessToken(): boolean {
  return Boolean(
    localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token')
  )
}

export function clearAccessToken(): void {
  localStorage.removeItem('access_token')
  sessionStorage.removeItem('access_token')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isAuthResponse(value: unknown): value is AuthResponse {
  if (!isRecord(value) || !isRecord(value.user)) {
    return false
  }

  return (
    typeof value.message === 'string' &&
    typeof value.user.id === 'number' &&
    typeof value.user.full_name === 'string' &&
    typeof value.user.email === 'string' &&
    typeof value.user.created_at === 'string' &&
    (value.access_token === undefined ||
      typeof value.access_token === 'string')
  )
}

async function requestAuth(
  action: 'register' | 'login',
  details: RegisterDetails | LoginDetails
): Promise<AuthResponse> {
  let response: Response

  try {
    response = await fetch(`${apiBaseUrl}/api/auth/${action}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(details),
    })
  } catch {
    throw new Error('Unable to connect to the server. Please try again.')
  }

  let data: unknown

  try {
    data = await response.json()
  } catch {
    throw new Error('The server returned an invalid response.')
  }

  if (!response.ok) {
    const message =
      isRecord(data) && typeof data.error === 'string'
        ? data.error
        : `The request failed (${response.status}).`
    throw new Error(message)
  }

  if (!isAuthResponse(data)) {
    throw new Error('The server returned an invalid response.')
  }

  return data
}

export async function registerAccount(
  details: RegisterDetails
): Promise<void> {
  await requestAuth('register', details)
}

export async function loginAccount(
  details: LoginDetails
): Promise<{ accessToken: string }> {
  const response = await requestAuth('login', details)

  if (!response.access_token) {
    throw new Error('The server did not return an access token.')
  }

  return { accessToken: response.access_token }
}
