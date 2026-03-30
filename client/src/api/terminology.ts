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

export interface Terminology {
  id: number
  user_id: number
  name: string
  term_type?: string
  datasource_id?: number
  synonyms?: string
  description?: string
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface TerminologyForm {
  name: string
  term_type?: string
  datasource_id?: number
  synonyms?: string
  description?: string
  enabled?: boolean
}

export interface TermType {
  value: string
  label: string
}

export const terminologyApi = {
  list: (params?: { datasource_id?: number; term_type?: string }) => {
    return request.get<Terminology[]>('/terminology', { params })
  },

  create: (data: TerminologyForm) => {
    return request.post<{ id: number; message: string }>('/terminology', data)
  },

  update: (id: number, data: Partial<TerminologyForm>) => {
    return request.put<{ message: string }>(`/terminology/${id}`, data)
  },

  delete: (id: number) => {
    return request.delete<{ message: string }>(`/terminology/${id}`)
  },

  getTypes: () => {
    return request.get<TermType[]>('/terminology/types')
  },
}
