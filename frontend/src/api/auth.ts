/**
AI Call Analytics — Authentication & Workspace API Service.
 */

import { apiClient } from './client'

export interface CompanyResponse {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserResponse {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'analyst' | 'viewer'
  is_active: boolean
  company_id: string
  company?: CompanyResponse
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in_minutes: number
  user: UserResponse
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  company_name: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface SwitchCompanyRequest {
  company_id: string
}

export const authApi = {
  login: (payload: LoginRequest): Promise<TokenResponse> =>
    apiClient<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  register: (payload: RegisterRequest): Promise<TokenResponse> =>
    apiClient<TokenResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMe: (): Promise<UserResponse> =>
    apiClient<UserResponse>('/api/v1/auth/me', {
      method: 'GET',
    }),

  listCompanies: (): Promise<CompanyResponse[]> =>
    apiClient<CompanyResponse[]>('/api/v1/auth/companies', {
      method: 'GET',
    }),

  switchCompany: (companyId: string): Promise<TokenResponse> =>
    apiClient<TokenResponse>('/api/v1/auth/switch-company', {
      method: 'POST',
      body: JSON.stringify({ company_id: companyId }),
    }),
}
