import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Add auth token to requests
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await request.post('/auth/login', { username, password })
  return data
}

export async function register(username: string, password: string, email?: string) {
  const { data } = await request.post('/auth/register', { username, password, email })
  return data
}

export async function getCurrentUser() {
  const { data } = await request.get('/auth/me')
  return data
}
