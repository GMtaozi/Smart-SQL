import { defineStore } from 'pinia'
import { ref } from 'vue'
import { generateSQL, executeSQL, getQueryHistory, submitFeedback } from '@/api/query'
import { getDatasources } from '@/api/schema'

export interface QueryResult {
  success: boolean
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  execution_time_ms: number
  error?: string
}

export interface GeneratedSQL {
  success: boolean
  sql: string
  used_tables: string[]
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

export const useQueryStore = defineStore('query', () => {
  const generatedSQL = ref<GeneratedSQL | null>(null)
  const queryResult = ref<QueryResult | null>(null)
  const loading = ref(false)
  const history = ref<QueryHistoryItem[]>([])
  const datasources = ref<{ id: number; name: string }[]>([])

  async function generate(userQuery: string, datasourceId: number) {
    loading.value = true
    try {
      generatedSQL.value = await generateSQL(userQuery, datasourceId)
      queryResult.value = null
    } finally {
      loading.value = false
    }
  }

  async function execute(sql: string, datasourceId: number) {
    loading.value = true
    try {
      queryResult.value = await executeSQL(sql, datasourceId)
      return queryResult.value
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory(limit = 50, offset = 0) {
    loading.value = true
    try {
      history.value = await getQueryHistory(limit, offset)
    } finally {
      loading.value = false
    }
  }

  async function fetchDatasources() {
    try {
      datasources.value = await getDatasources()
    } catch {
      datasources.value = []
    }
  }

  async function feedback(queryLogId: number, isCorrect: boolean, rating?: number, correctedSql?: string) {
    return await submitFeedback(queryLogId, isCorrect, rating, correctedSql)
  }

  function clearGeneratedSQL() {
    generatedSQL.value = null
    queryResult.value = null
  }

  return {
    generatedSQL,
    queryResult,
    loading,
    history,
    datasources,
    generate,
    execute,
    fetchHistory,
    fetchDatasources,
    feedback,
    clearGeneratedSQL,
  }
})
