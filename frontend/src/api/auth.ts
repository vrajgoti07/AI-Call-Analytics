/**
AI Call Analytics — Authentication & Workspace API Service.
 */

import { apiClient } from './client'

export type UserRole = 'ADMIN' | 'COMPANY'

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
  role: UserRole
  is_active: boolean
  company_id: string | null
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

export interface ForgotPasswordRequest {
  email: string
}

export interface ResetPasswordRequest {
  email: string
  new_password: string
}

export interface SwitchCompanyRequest {
  company_id: string
}

export interface AdminCompanyItem {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
  updated_at: string
  user_count: number
  call_count: number
  batch_count: number
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

  forgotPassword: (payload: ForgotPasswordRequest): Promise<{ message: string; status: string }> =>
    apiClient<{ message: string; status: string }>('/api/v1/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  resetPassword: (payload: ResetPasswordRequest): Promise<{ message: string; status: string }> =>
    apiClient<{ message: string; status: string }>('/api/v1/auth/reset-password', {
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

  listAdminCompanies: (): Promise<AdminCompanyItem[]> =>
    apiClient<AdminCompanyItem[]>('/api/v1/admin/companies', {
      method: 'GET',
    }),

  updateCompanyStatus: (companyId: string, isActive: boolean): Promise<AdminCompanyItem> =>
    apiClient<AdminCompanyItem>(`/api/v1/admin/companies/${companyId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    }),
}
