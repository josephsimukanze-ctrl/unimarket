export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  phone: string
  full_name: string
}

export interface LoginResponse {
  user: User
  access: string
  refresh: string
}

export interface RegisterPayload {
  email: string
  password: string
  password_confirm: string
  first_name?: string
  last_name?: string
  phone?: string
}

export interface LoginPayload {
  email: string
  password: string
}
