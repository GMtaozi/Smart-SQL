<template>
  <div class="datasource-page">
    <div class="page-header">
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加数据源
      </el-button>
    </div>

    <el-table :data="datasources" v-loading="loading" stripe>
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column prop="db_type" label="类型" width="120">
        <template #default="{ row }">
          <el-tag>{{ getDbTypeName(row.db_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="host" label="主机" min-width="150" show-overflow-tooltip />
      <el-table-column prop="port" label="端口" width="80" />
      <el-table-column prop="database_name" label="数据库" min-width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '活跃' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleViewTables(row)">已同步表</el-button>
          <el-button link type="primary" @click="handleSyncTables(row)">同步表结构</el-button>
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑数据源' : '添加数据源'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="数据源显示名称" />
        </el-form-item>

        <el-form-item label="数据库类型" prop="db_type">
          <el-select v-model="form.db_type" placeholder="选择数据库类型" @change="handleDbTypeChange">
            <el-option v-for="db in dbTypes" :key="db.value" :label="db.label" :value="db.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="主机" prop="host">
          <el-input v-model="form.host" placeholder="例如: localhost 或 192.168.1.100" />
        </el-form-item>

        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>

        <el-form-item label="数据库名" prop="database_name">
          <el-input v-model="form.database_name" placeholder="数据库名称" />
        </el-form-item>

        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="数据库用户名" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="数据库密码" />
        </el-form-item>

        <el-form-item v-if="showSchema" label="Schema">
          <el-input v-model="form.db_schema" placeholder="Schema 名称" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button @click="handleTestConnection" :loading="testing" :disabled="!canTest">
          <el-icon><Connection /></el-icon>
          测试连接
        </el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Sync Tables Dialog -->
    <el-dialog v-model="syncDialogVisible" title="同步表结构" width="800px">
      <div class="sync-header">
        <el-input v-model="tableSearch" placeholder="搜索表名..." prefix-icon="Search" clearable style="width: 300px; margin-right: 16px;" />
        <el-button @click="loadRemoteTables" :loading="loadingTables">刷新表列表</el-button>
      </div>

      <el-table ref="tableSelectRef" :data="filteredRemoteTables" v-loading="loadingTables" height="400" @selection-change="handleTableSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="table_name" label="表名" min-width="200" />
        <el-table-column prop="table_comment" label="备注" min-width="200" show-overflow-tooltip />
      </el-table>

      <div class="sync-footer">
        <span>已选择: {{ selectedTables.length }} 个表</span>
        <el-button @click="syncDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSyncSubmit" :loading="syncing" :disabled="selectedTables.length === 0">
          同步选中表结构
        </el-button>
      </div>
    </el-dialog>

    <!-- View Synced Tables Dialog -->
    <el-dialog v-model="viewTablesDialogVisible" title="已同步的表结构" width="900px">
      <div class="sync-header">
        <span>数据源: {{ currentViewDatasource?.name }}</span>
        <el-input v-model="viewTableSearch" placeholder="搜索表名..." prefix-icon="Search" clearable style="width: 250px; margin-left: 16px;" />
      </div>

      <el-table :data="filteredViewTables" v-loading="loadingViewTables" height="450" stripe>
        <el-table-column prop="table_name" label="表名" min-width="150" />
        <el-table-column prop="table_comment" label="表备注" min-width="200" show-overflow-tooltip />
        <el-table-column label="字段数" width="80" align="center">
          <template #default="{ row }">{{ row.columns?.length || 0 }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleViewTableColumns(row)">查看字段</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- View Table Columns Dialog -->
    <el-dialog v-model="viewColumnsDialogVisible" :title="`表结构: ${currentViewTable?.table_name}`" width="700px">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="表名">{{ currentViewTable?.table_name }}</el-descriptions-item>
        <el-descriptions-item label="表备注">{{ currentViewTable?.table_comment || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-table :data="currentViewTable?.columns || []" height="350" stripe style="margin-top: 16px;">
        <el-table-column prop="column_name" label="字段名" min-width="150" />
        <el-table-column prop="data_type" label="数据类型" width="120" />
        <el-table-column prop="is_primary_key" label="主键" width="60" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_primary_key" type="warning" size="small">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_nullable" label="可空" width="60" align="center">
          <template #default="{ row }">
            <span>{{ row.is_nullable ? '是' : '否' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="column_comment" label="字段备注" min-width="150" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus, Connection, Search } from '@element-plus/icons-vue'
import { datasourceApi, Datasource, DatasourceForm } from '@/api/datasource'
import { schemaApi, getTables, TableSchema } from '@/api/schema'

const loading = ref(false)
const submitting = ref(false)
const testing = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const datasources = ref<Datasource[]>([])
const formRef = ref<FormInstance>()

// Sync tables dialog
const syncDialogVisible = ref(false)
const loadingTables = ref(false)
const syncing = ref(false)
const remoteTables = ref<{ table_name: string; table_comment: string }[]>([])
const selectedTables = ref<string[]>([])
const tableSearch = ref('')
const currentSyncDatasourceId = ref<number | null>(null)
const tableSelectRef = ref()

// View synced tables dialog
const viewTablesDialogVisible = ref(false)
const loadingViewTables = ref(false)
const viewTables = ref<TableSchema[]>([])
const viewTableSearch = ref('')
const currentViewDatasource = ref<Datasource | null>(null)

// View table columns dialog
const viewColumnsDialogVisible = ref(false)
const currentViewTable = ref<TableSchema | null>(null)

interface RemoteTable {
  table_name: string
  table_comment: string
}

const canTest = computed(() => {
  return form.host && form.port && form.database_name && form.username && form.password
})

const dbTypes = [
  { value: 'mysql', label: 'MySQL' },
  { value: 'pg', label: 'PostgreSQL' },
  { value: 'oracle', label: 'Oracle' },
  { value: 'ck', label: 'ClickHouse' },
  { value: 'sqlServer', label: 'SQL Server' },
  { value: 'doris', label: 'Apache Doris' },
  { value: 'starrocks', label: 'StarRocks' },
  { value: 'es', label: 'Elasticsearch' },
  { value: 'kingbase', label: 'Kingbase' },
  { value: 'dm', label: '达梦 DM' },
  { value: 'redshift', label: 'AWS Redshift' },
]

const defaultPorts: Record<string, number> = {
  mysql: 3306,
  pg: 5432,
  oracle: 1521,
  ck: 8123,
  sqlServer: 1433,
  doris: 9030,
  starrocks: 9030,
  es: 9200,
  kingbase: 54321,
  dm: 5236,
  redshift: 5439,
}

const showSchemaTypes = ['sqlServer', 'pg', 'oracle', 'dm', 'redshift', 'kingbase']

const form = reactive<DatasourceForm>({
  name: '',
  host: '',
  port: 3306,
  database_name: '',
  username: '',
  password: '',
  db_type: 'mysql',
  db_schema: '',
})

const rules = computed<FormRules>(() => ({
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  // 编辑时密码非必填（允许保持现有密码）
  password: [{ required: !isEdit.value, message: '请输入密码', trigger: 'blur' }],
}))

const showSchema = computed(() => showSchemaTypes.includes(form.db_type))

const getDbTypeName = (type: string) => {
  return dbTypes.find(db => db.value === type)?.label || type
}

const handleDbTypeChange = (type: string) => {
  form.port = defaultPorts[type] || 5432
}

const handleTestConnection = async () => {
  testing.value = true
  try {
    const res = await datasourceApi.testConnection({
      db_type: form.db_type,
      host: form.host,
      port: form.port!,
      database_name: form.database_name,
      username: form.username,
      password: form.password,
      db_schema: form.db_schema || undefined,
    })
    if (res.data.success) {
      ElMessage.success(res.data.message)
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '测试连接失败')
  } finally {
    testing.value = false
  }
}

const loadDatasources = async () => {
  loading.value = true
  try {
    const res = await datasourceApi.list()
    datasources.value = res.data
  } catch (error) {
    ElMessage.error('加载数据源失败')
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row: Datasource) => {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.host = row.host
  form.port = row.port || defaultPorts[row.db_type] || 3306
  form.database_name = row.database_name
  form.username = row.username
  form.password = ''
  form.db_type = row.db_type
  form.db_schema = row.db_schema || ''
  dialogVisible.value = true
}

const resetForm = () => {
  form.name = ''
  form.host = ''
  form.port = 3306
  form.database_name = ''
  form.username = ''
  form.password = ''
  form.db_type = 'mysql'
  form.db_schema = ''
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (isEdit.value && editingId.value) {
      await datasourceApi.update(editingId.value, form)
      ElMessage.success('数据源更新成功')
    } else {
      await datasourceApi.create(form)
      ElMessage.success('数据源添加成功')
    }

    dialogVisible.value = false
    loadDatasources()
  } catch (error: any) {
    if (!error.errors) {
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: Datasource) => {
  try {
    await ElMessageBox.confirm('确定要删除这个数据源吗？', '提示', { type: 'warning' })
    await datasourceApi.delete(row.id)
    ElMessage.success('删除成功')
    loadDatasources()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// Sync tables functionality
const filteredRemoteTables = computed(() => {
  if (!tableSearch.value) return remoteTables.value
  const search = tableSearch.value.toLowerCase()
  return remoteTables.value.filter(t =>
    t.table_name.toLowerCase().includes(search) ||
    t.table_comment.toLowerCase().includes(search)
  )
})

const handleSyncTables = async (row: Datasource) => {
  currentSyncDatasourceId.value = row.id
  syncDialogVisible.value = true
  selectedTables.value = []
  tableSearch.value = ''
  await loadRemoteTables()
}

const loadRemoteTables = async () => {
  if (!currentSyncDatasourceId.value) return
  loadingTables.value = true
  try {
    const res = await schemaApi.getRemoteTables(currentSyncDatasourceId.value)
    remoteTables.value = res.data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取表列表失败')
    remoteTables.value = []
  } finally {
    loadingTables.value = false
  }
}

const handleTableSelectionChange = (selection: RemoteTable[]) => {
  selectedTables.value = selection.map(t => t.table_name)
}

const handleSyncSubmit = async () => {
  if (!currentSyncDatasourceId.value || selectedTables.value.length === 0) return
  syncing.value = true
  try {
    await schemaApi.syncTables(currentSyncDatasourceId.value, selectedTables.value)
    ElMessage.success(`成功同步 ${selectedTables.value.length} 个表的结构`)
    syncDialogVisible.value = false
    // Refresh synced tables list if the view dialog is open
    if (viewTablesDialogVisible.value && currentViewDatasource.value) {
      await loadViewTables(currentViewDatasource.value.id)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '同步表结构失败')
  } finally {
    syncing.value = false
  }
}

// View synced tables functionality
const filteredViewTables = computed(() => {
  if (!viewTableSearch.value) return viewTables.value
  const search = viewTableSearch.value.toLowerCase()
  return viewTables.value.filter(t =>
    t.table_name.toLowerCase().includes(search) ||
    (t.table_comment && t.table_comment.toLowerCase().includes(search))
  )
})

const handleViewTables = async (row: Datasource) => {
  currentViewDatasource.value = row
  viewTablesDialogVisible.value = true
  viewTableSearch.value = ''
  await loadViewTables(row.id)
}

const loadViewTables = async (datasourceId: number) => {
  loadingViewTables.value = true
  try {
    viewTables.value = await getTables(datasourceId)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取已同步表列表失败')
    viewTables.value = []
  } finally {
    loadingViewTables.value = false
  }
}

const handleViewTableColumns = (table: TableSchema) => {
  currentViewTable.value = table
  viewColumnsDialogVisible.value = true
}

onMounted(() => {
  loadDatasources()
})
</script>

<style scoped>
.datasource-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.sync-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.sync-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
