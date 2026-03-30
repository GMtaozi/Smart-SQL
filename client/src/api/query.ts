import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000, // 60s for query execution
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface GenerateSQLResponse {
  success: boolean
  sql: string
  used_tables: string[]
  error?: string
}

export interface ExecuteSQLResponse {
  success: boolean
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  execution_time_ms: number
  error?: string
}

export interface QueryHistoryItem {
  id: number
  user_query: string
  generated_sql: string
  status: string
  execution_time_ms?: number
  row_count?: number
  used_tables?: string[]
  created_at: string
}

export async function generateSQL(userQuery: string, datasourceId: number): Promise<GenerateSQLResponse> {
  const { data } = await request.post('/query/generate', {
    user_query: userQuery,
    datasource_id: datasourceId,
  })
  return data
}

export async function executeSQL(sql: string, datasourceId: number): Promise<ExecuteSQLResponse> {
  const { data } = await request.post('/query/execute', {
    sql,
    datasource_id: datasourceId,
  })
  return data
}

export async function getQueryHistory(limit = 50, offset = 0): Promise<QueryHistoryItem[]> {
  const { data } = await request.get('/query/history', {
    params: { limit, offset },
  })
  return data
}

export async function submitFeedback(
  queryLogId: number,
  isCorrect: boolean,
  rating?: number,
  correctedSql?: string
) {
  const { data } = await request.post('/query/feedback', {
    query_log_id: queryLogId,
    is_correct: isCorrect,
    rating,
    corrected_sql: correctedSql,
  })
  return data
}
