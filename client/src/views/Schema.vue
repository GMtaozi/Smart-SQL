<template>
  <div class="schema-container">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <h1>Schema 管理</h1>
      </div>
      <div class="header-right">
        <el-button @click="router.push('/')">返回查询</el-button>
        <el-button type="primary" @click="showAddDatasource = true">添加数据源</el-button>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="main">
      <!-- Datasources List -->
      <el-card class="card">
        <template #header>
          <span>数据源列表</span>
        </template>
        <el-table :data="datasources" stripe>
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="host" label="主机" />
          <el-table-column prop="port" label="端口" />
          <el-table-column prop="database_name" label="数据库" />
          <el-table-column prop="db_type" label="类型" width="100" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button text type="primary" @click="loadTables(row.id)">查看表</el-button>
              <el-button text type="danger" @click="handleDeleteDatasource(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- Tables for selected datasource -->
      <el-card v-if="selectedDatasourceId" class="card" style="margin-top: 16px;">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>表结构 - {{ selectedDatasourceId }}</span>
            <el-button type="primary" size="small" @click="showAddTable = true">添加表</el-button>
          </div>
        </template>
        <el-table :data="tables" stripe>
          <el-table-column prop="table_name" label="表名" />
          <el-table-column prop="table_comment" label="注释" />
          <el-table-column label="列数" width="80">
            <template #default="{ row }">
              {{ row.columns?.length || 0 }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button text type="primary" @click="viewTableDetail(row)">详情</el-button>
              <el-button text type="danger" @click="handleDeleteTable(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- Table Detail Dialog -->
      <el-dialog v-model="showTableDetail" title="表结构详情" width="600px">
        <el-descriptions v-if="selectedTable" :column="2" border>
          <el-descriptions-item label="表名">{{ selectedTable.table_name }}</el-descriptions-item>
          <el-descriptions-item label="注释">{{ selectedTable.table_comment || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="selectedTable?.columns || []" style="margin-top: 16px;">
          <el-table-column prop="column_name" label="列名" />
          <el-table-column prop="data_type" label="类型" />
          <el-table-column prop="column_comment" label="注释" />
          <el-table-column label="主键" width="60">
            <template #default="{ row }">
              {{ row.is_primary_key ? '是' : '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-dialog>

      <!-- Add Datasource Dialog -->
      <el-dialog v-model="showAddDatasource" title="添加数据源" width="500px">
        <el-form :model="datasourceForm" label-width="100px">
          <el-form-item label="名称">
            <el-input v-model="datasourceForm.name" placeholder="数据源名称" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="datasourceForm.db_type" style="width: 100%">
              <el-option label="PostgreSQL" value="postgresql" />
              <el-option label="MySQL" value="mysql" />
            </el-select>
          </el-form-item>
          <el-form-item label="主机">
            <el-input v-model="datasourceForm.host" placeholder="localhost" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input-number v-model="datasourceForm.port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="数据库">
            <el-input v-model="datasourceForm.database_name" placeholder="数据库名" />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="datasourceForm.username" placeholder="用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="datasourceForm.password" type="password" show-password />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showAddDatasource = false">取消</el-button>
          <el-button type="primary" @click="handleAddDatasource">确定</el-button>
        </template>
      </el-dialog>
    </el-main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDatasources, deleteDatasource, getTables, deleteTableSchema } from '@/api/schema'
import type { Datasource, TableSchema } from '@/types'

const router = useRouter()

const datasources = ref<Datasource[]>([])
const tables = ref<TableSchema[]>([])
const selectedDatasourceId = ref<number | null>(null)
const selectedTable = ref<TableSchema | null>(null)

const showAddDatasource = ref(false)
const showAddTable = ref(false)
const showTableDetail = ref(false)

const datasourceForm = reactive({
  name: '',
  host: 'localhost',
  port: 5432,
  database_name: '',
  username: '',
  password: '',
  db_type: 'postgresql',
})

onMounted(async () => {
  await loadDatasources()
})

async function loadDatasources() {
  datasources.value = await getDatasources()
}

async function loadTables(datasourceId: number) {
  selectedDatasourceId.value = datasourceId
  tables.value = await getTables(datasourceId)
}

async function handleAddDatasource() {
  try {
    const { createDatasource } = await import('@/api/schema')
    await createDatasource(datasourceForm)
    ElMessage.success('添加成功')
    showAddDatasource.value = false
    await loadDatasources()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '添加失败')
  }
}

async function handleDeleteDatasource(id: number) {
  await ElMessageBox.confirm('确认删除该数据源？', '警告', { type: 'warning' })
  await deleteDatasource(id)
  ElMessage.success('删除成功')
  await loadDatasources()
  if (selectedDatasourceId.value === id) {
    selectedDatasourceId.value = null
    tables.value = []
  }
}

async function handleDeleteTable(id: number) {
  await ElMessageBox.confirm('确认删除该表结构？', '警告', { type: 'warning' })
  await deleteTableSchema(id)
  ElMessage.success('删除成功')
  if (selectedDatasourceId.value) {
    await loadTables(selectedDatasourceId.value)
  }
}

function viewTableDetail(table: TableSchema) {
  selectedTable.value = table
  showTableDetail.value = true
}
</script>

<style scoped>
.schema-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
}

.header-left h1 {
  font-size: 20px;
  margin: 0;
  color: #409eff;
}

.main {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #f5f7fa;
}

.card {
  margin-bottom: 16px;
}
</style>
