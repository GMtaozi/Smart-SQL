<template>
  <div class="query-container">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <h1>SQLbot</h1>
      </div>
      <div class="header-right">
        <el-select v-model="selectedDatasource" placeholder="选择数据源" style="width: 200px; margin-right: 16px;">
          <el-option
            v-for="ds in queryStore.datasources"
            :key="ds.id"
            :label="ds.name"
            :value="ds.id"
          />
        </el-select>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            {{ authStore.user?.username }}
            <el-icon><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="schema">Schema 管理</el-dropdown-item>
              <el-dropdown-item command="history">查询历史</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="main">
      <!-- Query Input -->
      <el-card class="query-input-card">
        <template #header>
          <span>自然语言查询</span>
        </template>
        <el-input
          v-model="userQuery"
          type="textarea"
          :rows="3"
          placeholder="例如：查询本月销售额最高的前10个产品"
          @keyup.ctrl.enter="handleGenerate"
        />
        <div style="margin-top: 16px; text-align: right;">
          <el-button type="primary" :loading="queryStore.loading" @click="handleGenerate">
            生成 SQL
          </el-button>
        </div>
      </el-card>

      <!-- SQL Preview & Execute -->
      <SqlViewer
        v-if="queryStore.generatedSQL"
        :sql="queryStore.generatedSQL.sql!"
        :used-tables="queryStore.generatedSQL.used_tables || []"
        :datasource-id="selectedDatasource"
        @execute="handleExecute"
        @clear="queryStore.clearGeneratedSQL"
      />

      <!-- Result Table -->
      <ResultTable
        v-if="queryStore.queryResult"
        :result="queryStore.queryResult"
      />
    </el-main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useQueryStore } from '@/stores/query'
import SqlViewer from '@/components/SqlViewer.vue'
import ResultTable from '@/components/ResultTable.vue'
import SchemaSelector from '@/components/SchemaSelector.vue'

const router = useRouter()
const authStore = useAuthStore()
const queryStore = useQueryStore()

const userQuery = ref('')
const selectedDatasource = ref<number | null>(null)

onMounted(async () => {
  await queryStore.fetchDatasources()
  if (queryStore.datasources.length > 0) {
    selectedDatasource.value = queryStore.datasources[0].id
  }
})

async function handleGenerate() {
  if (!userQuery.value.trim()) {
    ElMessage.warning('请输入查询内容')
    return
  }
  if (!selectedDatasource.value) {
    ElMessage.warning('请选择数据源')
    return
  }

  await queryStore.generate(userQuery.value, selectedDatasource.value)

  if (!queryStore.generatedSQL?.success) {
    ElMessage.error(queryStore.generatedSQL?.error || 'SQL 生成失败')
  }
}

async function handleExecute(sql: string) {
  if (!selectedDatasource.value) {
    ElMessage.error('请先选择数据源')
    return
  }
  const result = await queryStore.execute(sql, selectedDatasource.value)
  if (result?.success) {
    ElMessage.success(`查询成功，返回 ${result.row_count} 行，耗时 ${result.execution_time_ms?.toFixed(0) ?? 0}ms`)
  } else {
    ElMessage.error(result?.error || '查询执行失败')
  }
}

function handleCommand(command: string) {
  switch (command) {
    case 'schema':
      router.push('/schema')
      break
    case 'history':
      router.push('/history')
      break
    case 'logout':
      authStore.logout()
      router.push('/login')
      break
  }
}
</script>

<style scoped>
.query-container {
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

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.main {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #f5f7fa;
}

.query-input-card {
  margin-bottom: 16px;
}
</style>
