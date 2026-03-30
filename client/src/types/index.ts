// TypeScript type definitions

export interface User {
  id: number
  username: string
  email?: string
}

export interface Datasource {
  id: number
  name: string
  host: string
  port: number
  database_name: string
  db_type: string
}

export interface ColumnSchema {
  column_name: string
  data_type: string
  column_comment?: string
  is_primary_key: boolean
  is_nullable: boolean
}

export interface TableSchema {
  id: number
  table_name: string
  table_comment?: string
  columns: ColumnSchema[]
}

export interface QueryResult {
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  execution_time_ms: number
}

export interface QueryHistory {
  id: number
  user_query: string
  generated_sql: string
  status: string
  execution_time_ms?: number
  row_count?: number
  created_at: string
}
