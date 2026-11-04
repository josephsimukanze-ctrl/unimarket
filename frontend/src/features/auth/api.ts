import { apiClient } from '@/shared/api/client'
import type { LoginPayload, LoginResponse, RegisterPayload, User } from './types'

export async function registerUser(payload: RegisterPayload): Promise<User> {
  const { data } = await apiClient.post<User>('/api/v1/auth/register/', payload)
  return data
}

export async function loginUser(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/api/v1/auth/login/', payload)
  return data
}

export async function fetchMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/api/v1/auth/me/')
  return data
}
