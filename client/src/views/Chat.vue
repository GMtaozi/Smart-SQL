<template>
  <div class="chat-page">
    <el-card class="chat-card">
      <template #header>
        <div class="chat-header">
          <div class="datasource-select">
            <span class="label">数据源:</span>
            <el-select v-model="selectedDatasourceId" placeholder="选择数据源">
              <el-option
                v-for="ds in datasources"
                :key="ds.id"
                :label="ds.name"
                :value="ds.id"
              />
            </el-select>
          </div>
          <div class="header-actions">
            <el-button v-if="!isScreenCleared && messages.length > 0" @click="handleClearScreen" size="small">
              <el-icon><Delete /></el-icon>
              清屏
            </el-button>
            <el-button v-if="isScreenCleared && hiddenMessages.length > 0" @click="handleRestoreScreen" size="small" type="primary">
              <el-icon><View /></el-icon>
              查看历史 ({{ hiddenMessages.length }} 条)
            </el-button>
          </div>
        </div>
      </template>

      <div class="chat-messages" ref="messagesContainer">
        <div v-if="messages.length === 0 || isScreenCleared" class="empty-state">
          <el-icon size="64" color="#1cba90"><ChatDotRound /></el-icon>
          <h3 v-if="!isScreenCleared">欢迎使用智能SQL助手</h3>
          <h3 v-else>屏幕已清空</h3>
          <p v-if="!isScreenCleared">输入自然语言问题，我将帮您生成 SQL 查询</p>
          <p v-else>当前没有显示的对话内容</p>
        </div>

        <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
          <div class="message-avatar">
            <el-avatar v-if="msg.role === 'user'" :size="36" icon="UserFilled" />
            <el-avatar v-else :size="36" color="#1cba90" icon="ChatDotRound" />
          </div>
          <div class="message-content">
            <div class="message-text" v-if="msg.role === 'user'">{{ msg.content }}</div>
            <div class="message-text sql-result" v-else>
              <div v-if="msg.sql" class="sql-block">
                <div class="sql-header">
                  <span>生成的 SQL</span>
                  <el-button size="small" text @click="copySql(msg.sql!)">
                    <el-icon><CopyDocument /></el-icon>
                    复制
                  </el-button>
                </div>
                <pre class="sql-code">{{ msg.sql }}</pre>
                <div class="sql-actions">
                  <el-button type="primary" @click="executeQuery(msg)" :loading="executing">
                    <el-icon><VideoPlay /></el-icon>
                    执行查询
                  </el-button>
                </div>
              </div>

              <div v-if="msg.result" class="result-block">
                <div class="result-header">
                  <div class="result-header-left">
                    <span>查询结果</span>
                    <span class="result-stats">{{ msg.totalCount || msg.rowCount || 0 }} 行 | {{ msg.executionTime || 0 }}ms</span>
                  </div>
                  <div class="view-switch" v-if="msg.result.length > 0">
                    <el-radio-group v-model="msg.viewMode" size="small">
                      <el-radio-button label="table">表格</el-radio-button>
                      <el-radio-button label="card" v-if="hasGroupData(msg)">卡片</el-radio-button>
                      <el-radio-button label="chart" v-if="canShowChart(msg)">图表</el-radio-button>
                    </el-radio-group>
                  </div>
                  <!-- Export button for large datasets -->
                  <div v-if="(msg.totalCount || 0) > 10" class="export-section">
                    <el-button
                      v-if="exportingMsgId !== messages.indexOf(msg)"
                      type="warning"
                      size="small"
                      @click="handleExport(msg)"
                    >
                      <el-icon><Download /></el-icon>
                      导出CSV
                    </el-button>
                    <el-tag v-else type="warning" size="small">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      导出中...
                    </el-tag>
                  </div>
                </div>
                <!-- Export hint -->
                <div v-if="(msg.totalCount || 0) > 10" class="export-hint">
                  <el-alert type="info" :closable="false" show-icon>
                    <template #title>
                      当前显示前{{ msg.rowCount || 0 }}行数据（共 {{ msg.totalCount }} 行），如需完整数据请点击「导出CSV」
                    </template>
                  </el-alert>
                </div>

                <!-- Table View -->
                <div v-if="msg.viewMode === 'table' || !msg.viewMode" class="table-view">
                  <el-table :data="msg.result" stripe border :max-height="350" size="small">
                    <el-table-column
                      v-for="col in msg.columns"
                      :key="col"
                      :prop="col"
                      :label="col"
                      show-overflow-tooltip
                      min-width="120"
                    />
                  </el-table>
                </div>

                <!-- Card View (for grouped data) -->
                <div v-else-if="msg.viewMode === 'card'" class="card-view">
                  <div v-if="hasGroupData(msg)" class="grouped-cards">
                    <el-card v-for="(group, idx) in getGroupedData(msg)" :key="idx" class="data-card" shadow="hover">
                      <template #header>
                        <div class="card-header">
                          <span class="group-title">{{ group.groupKey }}</span>
                          <el-tag size="small" type="info">{{ group.rows.length }} 条</el-tag>
                        </div>
                      </template>
                      <el-table :data="group.rows" size="small" border :show-header="true">
                        <el-table-column
                          v-for="col in getNonGroupColumns(msg)"
                          :key="col"
                          :prop="col"
                          :label="col"
                          show-overflow-tooltip
                        />
                      </el-table>
                    </el-card>
                  </div>
                  <div v-else class="table-view">
                    <el-table :data="msg.result" stripe border :max-height="350" size="small">
                      <el-table-column
                        v-for="col in msg.columns"
                        :key="col"
                        :prop="col"
                        :label="col"
                        show-overflow-tooltip
                        min-width="120"
                      />
                    </el-table>
                  </div>
                </div>

                <!-- Chart View -->
                <div v-else-if="msg.viewMode === 'chart'" class="chart-view">
                  <div v-if="canShowChart(msg)" class="chart-container">
                    <div class="chart-selector">
                      <el-select v-model="msg.chartType" placeholder="选择图表类型" size="small">
                        <el-option label="柱状图" value="bar" />
                        <el-option label="饼图" value="pie" />
                        <el-option label="折线图" value="line" />
                      </el-select>
                      <el-select v-model="msg.xAxis" placeholder="选择X轴" size="small" v-if="msg.chartType === 'bar' || msg.chartType === 'line'">
                        <el-option v-for="col in msg.columns" :key="col" :label="col" :value="col" />
                      </el-select>
                      <el-select v-model="msg.yAxis" placeholder="选择Y轴" size="small">
                        <el-option v-for="col in getNumericColumns(msg)" :key="col" :label="col" :value="col" />
                      </el-select>
                    </div>
                    <div class="chart-placeholder">
                      <el-icon size="48" color="#c0c4cc"><DataAnalysis /></el-icon>
                      <p>图表展示区域</p>
                      <p class="chart-hint">X轴: {{ msg.xAxis || '未选择' }} | Y轴: {{ msg.yAxis || '未选择' }}</p>
                      <div class="simple-bar-chart" v-if="msg.chartType === 'bar' && msg.xAxis && msg.yAxis">
                        <div v-for="(item, idx) in msg.result.slice(0, 10)" :key="idx" class="bar-item">
                          <span class="bar-label">{{ item[msg.xAxis] }}</span>
                          <div class="bar-fill" :style="{ width: getBarWidth(item[msg.yAxis], getMaxValue(msg, msg.yAxis)) + '%' }"></div>
                          <span class="bar-value">{{ formatNumber(item[msg.yAxis]) }}</span>
                        </div>
                      </div>
                      <div class="simple-pie-chart" v-else-if="msg.chartType === 'pie' && msg.xAxis && msg.yAxis">
                        <div v-for="(item, idx) in msg.result.slice(0, 8)" :key="idx" class="pie-item">
                          <span class="pie-label">{{ item[msg.xAxis] }}</span>
                          <div class="pie-value">{{ formatNumber(item[msg.yAxis]) }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="table-view">
                    <el-table :data="msg.result" stripe border :max-height="350" size="small">
                      <el-table-column
                        v-for="col in msg.columns"
                        :key="col"
                        :prop="col"
                        :label="col"
                        show-overflow-tooltip
                        min-width="120"
                      />
                    </el-table>
                  </div>
                </div>
              </div>

              <div v-if="msg.error" class="error-block">
                <el-alert type="error" :title="msg.error" :closable="false" />
              </div>
            </div>
          </div>
        </div>

        <div v-if="generating" class="message assistant">
          <div class="message-avatar">
            <el-avatar :size="36" color="#1cba90" icon="ChatDotRound" />
          </div>
          <div class="message-content">
            <div class="message-text generating">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在生成 SQL...
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="userQuery"
          type="textarea"
          :rows="3"
          placeholder="输入自然语言问题，例如：查询所有订单金额大于1000的用户"
          @keydown.ctrl.enter="sendQuery"
        />
        <div class="input-actions">
          <span class="hint">Ctrl + Enter 发送</span>
          <el-button type="primary" @click="sendQuery" :disabled="!userQuery.trim() || generating" :loading="generating">
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, UserFilled, CopyDocument, VideoPlay, Promotion, Loading, DataAnalysis, Delete, View, Download } from '@element-plus/icons-vue'
import { generateSQL, executeSQL, createExportTask, getExportStatus } from '@/api/query'
import { datasourceApi } from '@/api/datasource'
import { useChatStore, type Message } from '@/stores/chat'
import { storeToRefs } from 'pinia'

// 使用 store 持久化聊天记录
const chatStore = useChatStore()

// 使用 storeToRefs 保持响应式
const { messages, generating, executing, selectedDatasourceId, hiddenMessages, isScreenCleared } = storeToRefs(chatStore)

const userQuery = ref('')
const datasources = ref<{ id: number; name: string }[]>([])
const messagesContainer = ref<HTMLElement | null>(null)

const loadDatasources = async () => {
  try {
    const res = await datasourceApi.list()
    datasources.value = res.data

    // Validate selectedDatasourceId belongs to current user
    if (selectedDatasourceId) {
      const exists = res.data.some((ds: any) => ds.id === selectedDatasourceId)
      if (!exists) {
        // Selected datasource no longer belongs to current user, clear it
        chatStore.setDatasource(null)
      }
    }

    // Auto-select first datasource if none selected
    if (res.data.length > 0 && !selectedDatasourceId) {
      chatStore.setDatasource(res.data[0].id)
    }
  } catch (error) {
    ElMessage.error('加载数据源失败')
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const sendQuery = async () => {
  if (!userQuery.value.trim() || !selectedDatasourceId.value) {
    ElMessage.warning('请输入问题并选择数据源')
    return
  }

  const query = userQuery.value.trim()
  userQuery.value = ''

  // 使用 store 方法添加消息
  chatStore.addUserMessage(query)
  chatStore.setGenerating(true)

  scrollToBottom()

  try {
    const res = await generateSQL(query, selectedDatasourceId.value)

    chatStore.setGenerating(false)

    if (res.success) {
      chatStore.addAssistantMessage({
        sql: res.sql,
        viewMode: 'table',
        chartType: 'bar',
      })
    } else {
      chatStore.addAssistantMessage({
        error: res.error || 'SQL 生成失败',
      })
    }
  } catch (error: any) {
    chatStore.setGenerating(false)
    chatStore.addAssistantMessage({
      error: error.response?.data?.detail || '请求失败',
    })
  }

  scrollToBottom()
}

const executeQuery = async (msg: Message) => {
  if (!msg.sql || !selectedDatasourceId.value) return

  chatStore.setExecuting(true)
  try {
    const res = await executeSQL(msg.sql, selectedDatasourceId.value)

    // 找到该消息在 messages 数组中的索引并更新
    const index = chatStore.messages.findIndex((m) => m === msg)
    if (index !== -1) {
      chatStore.updateAssistantMessage(index, {
        result: res.rows,
        columns: res.columns,
        rowCount: res.row_count,
        totalCount: res.total_count,
        executionTime: res.execution_time_ms,
        viewMode: msg.viewMode || 'table',
      })

      // Auto-detect chart settings
      if (res.columns.length > 0) {
        const numericCols = res.columns.filter((col: string) => {
          const val = (res.rows[0] as Record<string, unknown>)?.[col]
          return typeof val === 'number' || (!isNaN(parseFloat(String(val))) && isFinite(Number(val)))
        })
        if (numericCols.length > 0) {
          chatStore.updateAssistantMessage(index, {
            yAxis: numericCols[0],
            xAxis: res.columns.find((c: string) => c !== numericCols[0]) || res.columns[0],
          })
        }
      }
    }

    ElMessage.success('查询执行成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '查询执行失败')
  } finally {
    chatStore.setExecuting(false)
    scrollToBottom()
  }
}

const copySql = (sql: string) => {
  navigator.clipboard.writeText(sql)
  ElMessage.success('已复制到剪贴板')
}

// Export related state
const exportingTaskId = ref<string | null>(null)
const exportingMsgId = ref<number | null>(null)

// Check if result needs export (more than 10 rows)
const needsExport = (msg: Message): boolean => {
  return (msg.rowCount || 0) > 10
}

// Handle export
const handleExport = async (msg: Message) => {
  if (!msg.sql || !selectedDatasourceId.value) {
    console.log('[DEBUG] handleExport: missing sql or datasourceId', msg.sql, selectedDatasourceId.value)
    return
  }

  // Check if needs export based on total count
  const needsExport = (msg.totalCount || 0) > 10
  console.log('[DEBUG] handleExport: totalCount=', msg.totalCount, 'needsExport=', needsExport)
  if (!needsExport) return

  exportingMsgId.value = messages.value.indexOf(msg)
  exportingTaskId.value = null

  try {
    console.log('[DEBUG] handleExport: calling createExportTask', msg.sql)
    // Create export task
    const res = await createExportTask(msg.sql, selectedDatasourceId.value)
    console.log('[DEBUG] handleExport: task created', res)
    exportingTaskId.value = res.task_id

    ElMessage.info('正在导出数据，请稍候...')

    // Start polling for status
    pollExportStatus(res.task_id)
  } catch (error: any) {
    console.error('[DEBUG] handleExport error:', error)
    ElMessage.error(error.response?.data?.detail || '创建导出任务失败')
    exportingTaskId.value = null
    exportingMsgId.value = null
  }
}

// Poll export status until completed
const pollExportStatus = async (taskId: string) => {
  const poll = async () => {
    try {
      const statusRes = await getExportStatus(taskId)

      if (statusRes.status === 'completed' && statusRes.csv_content) {
        // Download CSV
        downloadCSV(statusRes.csv_content, `export_${taskId.slice(0, 8)}.csv`)
        ElMessage.success('导出成功，文件已开始下载')
        exportingTaskId.value = null
        exportingMsgId.value = null
        return
      } else if (statusRes.status === 'failed') {
        ElMessage.error('导出失败: ' + statusRes.error_message)
        exportingTaskId.value = null
        exportingMsgId.value = null
        return
      }

      // Continue polling
      if (exportingTaskId.value === taskId) {
        setTimeout(poll, 1000)
      }
    } catch (error: any) {
      console.error('[DEBUG] Poll export status error:', error)
      if (exportingTaskId.value === taskId) {
        setTimeout(poll, 2000)
      }
    }
  }

  poll()
}

// Download CSV file
const downloadCSV = (csvContent: string, filename: string) => {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

const handleClearScreen = () => {
  console.log('[DEBUG] handleClearScreen called, messages length:', messages.value.length)
  chatStore.clearScreen()
}

const handleRestoreScreen = () => {
  console.log('[DEBUG] handleRestoreScreen called, hiddenMessages length:', hiddenMessages.value.length)
  chatStore.restoreScreen()
  console.log('[DEBUG] after restoreScreen, messages length:', messages.value.length)
}

// Helper functions for view modes
const hasGroupData = (msg: Message): boolean => {
  if (!msg.result || msg.result.length === 0) return false
  // Simple heuristic: if result has more than 5 rows and columns include common group-by fields
  const groupFields = ['category', 'type', 'status', 'name', 'product', 'user', 'date', 'month', 'year']
  return msg.result.length > 5 && (msg.columns?.some((col: string) =>
    groupFields.some(g => col.toLowerCase().includes(g))
  ) ?? false)
}

const canShowChart = (msg: Message): boolean => {
  if (!msg.result || msg.result.length === 0) return false
  const numericCols = getNumericColumns(msg)
  return numericCols.length > 0 && !!(msg.columns && msg.columns.length >= 2)
}

const getNumericColumns = (msg: Message): string[] => {
  if (!msg.result || msg.result.length === 0) return []
  const firstRow = msg.result[0] as Record<string, unknown>
  return msg.columns?.filter((col: string) => {
    const val = firstRow[col]
    return typeof val === 'number' || (!isNaN(parseFloat(String(val))) && isFinite(Number(val)))
  }) || []
}

const getNonGroupColumns = (msg: Message): string[] => {
  if (!msg.columns) return []
  const groupFields = ['category', 'type', 'status', 'name', 'product', 'user', 'date', 'month', 'year', 'id']
  return msg.columns.filter((col: string) =>
    !groupFields.some(g => col.toLowerCase().includes(g))
  )
}

const getGroupedData = (msg: Message): { groupKey: string; rows: Record<string, unknown>[] }[] => {
  if (!msg.result || !msg.columns || msg.columns.length === 0) return []

  // Find the group column
  const groupFields = ['category', 'type', 'status', 'name', 'product', 'user', 'date', 'month', 'year']
  const groupCol = msg.columns.find((col: string) =>
    groupFields.some(g => col.toLowerCase().includes(g))
  ) || msg.columns[0]

  // Group rows
  const groups: Record<string, Record<string, unknown>[]> = {}
  for (const row of msg.result) {
    const key = String(row[groupCol] || '(无)')
    if (!groups[key]) groups[key] = []
    groups[key].push(row)
  }

  return Object.entries(groups).map(([key, rows]) => ({
    groupKey: key,
    rows
  }))
}

const getBarWidth = (value: number, maxValue: number): number => {
  if (!value || typeof value !== 'number' || !isFinite(value)) return 0
  if (!maxValue || typeof maxValue !== 'number' || maxValue === 0) return 0
  return Math.min(100, (value / maxValue) * 100)
}

const getMaxValue = (msg: Message, column: string): number => {
  if (!msg.result || msg.result.length === 0) return 0
  return Math.max(...msg.result.map((row: Record<string, unknown>) => {
    const val = row[column]
    return typeof val === 'number' ? val : parseFloat(String(val)) || 0
  }))
}

const formatNumber = (val: unknown): string => {
  if (typeof val === 'number') {
    if (val >= 1000000) return (val / 1000000).toFixed(1) + 'M'
    if (val >= 1000) return (val / 1000).toFixed(1) + 'K'
    return val.toFixed(0)
  }
  return String(val)
}

onMounted(() => {
  // 如果还没有加载过数据源，则加载
  if (datasources.value.length === 0) {
    loadDatasources()
  }
})
</script>

<style scoped>
.chat-page {
  height: calc(100vh - 140px);
}

.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 12px;
}

.chat-card :deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.chat-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.datasource-select {
  display: flex;
  align-items: center;
  gap: 12px;
}

.datasource-select .label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.datasource-select :deep(.el-select) {
  min-width: 200px;
}

.datasource-select :deep(.el-select .el-input__wrapper) {
  border-radius: 8px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #909399;
}

.empty-state h3 {
  margin: 16px 0 8px;
  color: #303133;
}

.message {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  max-width: 85%;
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  display: inline-block;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.message.user .message-text {
  background: #1cba90;
  color: #fff;
}

.message.assistant .message-text {
  background: #f5f7fa;
  color: #303133;
}

.message.assistant .message-text.generating {
  color: #909399;
}

.sql-block {
  margin-bottom: 16px;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f0f0f0;
  border-radius: 8px 8px 0 0;
  font-size: 13px;
  color: #606266;
}

.sql-code {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  margin: 0;
  border-radius: 0 0 8px 8px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.sql-actions {
  margin-top: 12px;
}

.result-block {
  margin-top: 16px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #e6f7f2;
  border-radius: 8px 8px 0 0;
  font-size: 13px;
  color: #1cba90;
}

.result-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-stats {
  color: #909399;
  font-size: 12px;
}

.view-switch {
  display: flex;
  align-items: center;
}

.view-switch :deep(.el-radio-group) {
  display: flex;
}

.error-block {
  margin-top: 12px;
}

.chat-input {
  padding: 16px 20px;
  border-top: 1px solid #f0f0f0;
  background: #fff;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.hint {
  font-size: 12px;
  color: #909399;
}

/* Card View Styles */
.table-view {
  background: #fff;
  border-radius: 0 0 8px 8px;
  overflow: hidden;
}

.card-view {
  background: #fff;
  border-radius: 0 0 8px 8px;
  padding: 12px;
}

.grouped-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.data-card {
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.data-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.data-card :deep(.el-card__body) {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.group-title {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

/* Chart View Styles */
.chart-view {
  background: #fff;
  border-radius: 0 0 8px 8px;
  padding: 12px;
}

.chart-container {
  min-height: 300px;
}

.chart-selector {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 250px;
  background: #fafafa;
  border-radius: 8px;
  color: #909399;
}

.chart-placeholder p {
  margin: 8px 0;
}

.chart-hint {
  font-size: 12px;
  color: #c0c4cc;
}

.simple-bar-chart {
  width: 100%;
  max-width: 600px;
  padding: 16px;
}

.bar-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  gap: 12px;
}

.bar-label {
  width: 80px;
  text-align: right;
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-fill {
  height: 20px;
  background: linear-gradient(90deg, #1cba90, #2ed573);
  border-radius: 4px;
  min-width: 4px;
  max-width: 300px;
  transition: width 0.3s ease;
}

.bar-value {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  min-width: 60px;
}

.simple-pie-chart {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  width: 100%;
  max-width: 500px;
  padding: 16px;
}

.pie-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.pie-label {
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.pie-value {
  font-size: 14px;
  font-weight: 600;
  color: #1cba90;
}
</style>
