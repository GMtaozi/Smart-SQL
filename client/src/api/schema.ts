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
  host: string
  port: number
  database_name: string
  username: string
  db_type: string
  is_active: boolean
  created_at: string
}

export interface ColumnSchema {
  column_name: string
  data_type: string
  column_comment?: string
  is_primary_key: boolean
  is_nullable: boolean
  column_id: number
}

export interface TableSchema {
  id: number
  datasource_id: number
  table_name: string
  table_comment?: string
  columns: ColumnSchema[]
  created_at: string
}

export async function createDatasource(params: {
  name: string
  host: string
  port: number
  database_name: string
  username: string
  password: string
  db_type: string
}): Promise<Datasource> {
  const { data } = await request.post('/schema/datasources', params)
  return data
}

export async function getDatasources(): Promise<Datasource[]> {
  const { data } = await request.get('/schema/datasources')
  return data
}

export async function deleteDatasource(id: number) {
  const { data } = await request.delete(`/schema/datasources/${id}`)
  return data
}

export async function createTableSchema(params: {
  datasource_id: number
  table_name: string
  table_comment?: string
  columns: ColumnSchema[]
}): Promise<TableSchema> {
  const { data } = await request.post('/schema/tables', params)
  return data
}

export async function getTables(datasourceId: number): Promise<TableSchema[]> {
  const { data } = await request.get('/schema/tables', {
    params: { datasource_id: datasourceId },
  })
  return data
}

export async function deleteTableSchema(tableId: number) {
  const { data } = await request.delete(`/schema/tables/${tableId}`)
  return data
}

// Remote table operations
export interface RemoteTable {
  table_name: string
  table_comment: string
}

export interface RemoteColumn {
  column_name: string
  data_type: string
  column_comment: string
  is_primary_key: boolean
  is_nullable: boolean
}

export const schemaApi = {
  // Get remote tables from datasource
  getRemoteTables: (datasourceId: number) => {
    return request.get<RemoteTable[]>(`/schema/datasources/${datasourceId}/tables`)
  },

  // Get remote columns for a table
  getRemoteColumns: (datasourceId: number, tableName: string) => {
    return request.get<RemoteColumn[]>(`/schema/datasources/${datasourceId}/tables/${tableName}/columns`)
  },

  // Sync selected tables - use 5 minute timeout for large syncs
  syncTables: (datasourceId: number, tableNames: string[]) => {
    return request.post<TableSchema[]>(`/schema/datasources/${datasourceId}/sync`, { table_names: tableNames }, {
      timeout: 300000,
    })
  },
}
