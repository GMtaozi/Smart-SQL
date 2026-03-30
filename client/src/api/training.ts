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

export interface TrainingData {
  id: number
  user_id: number
  question: string
  sql: string
  datasource_id?: number
  description?: string
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface TrainingForm {
  question: string
  sql: string
  datasource_id?: number
  description?: string
  enabled?: boolean
}

export const trainingApi = {
  list: (params?: { datasource_id?: number; enabled?: boolean; page?: number; page_size?: number }) => {
    return request.get<TrainingData[]>('/training', { params })
  },

  create: (data: TrainingForm) => {
    return request.post<{ id: number; message: string }>('/training', data)
  },

  update: (id: number, data: Partial<TrainingForm>) => {
    return request.put<{ message: string }>(`/training/${id}`, data)
  },

  delete: (id: number) => {
    return request.delete<{ message: string }>(`/training/${id}`)
  },

  batchDelete: (ids: number[]) => {
    return request.post<{ message: string }>('/training/batch-delete', { ids })
  },
}
