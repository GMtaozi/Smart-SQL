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

export interface Datasource {
  id: number
  user_id: number
  name: string
  description?: string
  host: string
  port?: number
  database_name: string
  username: string
  db_type: string
  db_schema?: string
  extra_params?: string
  timeout?: number
  ssl?: boolean
  is_active: boolean
  created_at?: string
}

export interface DatasourceForm {
  name: string
  description?: string
  host: string
  port?: number
  database_name: string
  username: string
  password: string
  db_type: string
  db_schema?: string
  extra_params?: string
  timeout?: number
  ssl?: boolean
}

export const datasourceApi = {
  list: () => {
    return request.get<Datasource[]>('/schema/datasources')
  },

  create: (data: DatasourceForm) => {
    return request.post<{ id: number; message: string }>('/schema/datasources', data)
  },

  update: (id: number, data: Partial<DatasourceForm>) => {
    return request.put<{ message: string }>(`/schema/datasources/${id}`, data)
  },

  delete: (id: number) => {
    return request.delete<{ message: string }>(`/schema/datasources/${id}`)
  },

  testConnection: (data: {
    db_type: string
    host: string
    port: number
    database_name: string
    username: string
    password: string
    db_schema?: string
    extra_params?: string
  }) => {
    return request.post<{ success: boolean; message: string }>('/schema/datasources/test-connection', data)
  },
}
