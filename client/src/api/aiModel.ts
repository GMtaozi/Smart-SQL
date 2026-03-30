import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface AIModel {
  id: number
  name: string
  supplier: string
  supplier_name: string
  model_type: number
  base_model: string
  api_key: string
  api_domain?: string
  is_default: boolean
  protocol: number
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface AIModelForm {
  name: string
  supplier: string
  model_type?: number
  base_model: string
  api_key: string
  api_domain?: string
  is_default?: boolean
  config_list?: Record<string, any>
  protocol?: number
  enabled?: boolean
}

export interface Supplier {
  value: string
  label: string
}

export const aiModelApi = {
  list: () => {
    return request.get<AIModel[]>('/ai-model')
  },

  create: (data: AIModelForm) => {
    return request.post<{ id: number; message: string }>('/ai-model', data)
  },

  update: (id: number, data: Partial<AIModelForm>) => {
    return request.put<{ message: string }>(`/ai-model/${id}`, data)
  },

  delete: (id: number) => {
    return request.delete<{ message: string }>(`/ai-model/${id}`)
  },

  setDefault: (id: number) => {
    return request.post<{ message: string }>(`/ai-model/${id}/default`)
  },

  test: (data: { api_key: string; model: string; supplier: string; api_domain?: string; config_list?: any }) => {
    return request.post<{ success: boolean; message: string }>('/ai-model/test', data)
  },

  getSuppliers: () => {
    return request.get<{ suppliers: Supplier[] }>('/ai-model/suppliers')
  },
}
