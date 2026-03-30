<template>
  <div class="history-container">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <h1>查询历史</h1>
      </div>
      <div class="header-right">
        <el-button @click="router.push('/')">返回查询</el-button>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="main">
      <el-card>
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>历史记录</span>
            <el-button text @click="loadHistory">
              <el-icon><refresh /></el-icon>
            </el-button>
          </div>
        </template>

        <el-table :data="queryStore.history" stripe v-loading="queryStore.loading">
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="user_query" label="用户问题" min-width="200" />
          <el-table-column prop="generated_sql" label="生成SQL" min-width="300">
            <template #default="{ row }">
              <el-tooltip :content="row.generated_sql" placement="top" :show-after="300">
                <span class="sql-preview">{{ row.generated_sql }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="row_count" label="行数" width="80">
            <template #default="{ row }">
              {{ row.row_count ?? '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="execution_time_ms" label="耗时" width="100">
            <template #default="{ row }">
              {{ row.execution_time_ms ? row.execution_time_ms.toFixed(0) + 'ms' : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="反馈" width="120">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'success'"
                text
                type="primary"
                size="small"
                @click="showFeedback(row)"
              >
                评价
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 16px; text-align: right;">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="20"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="loadHistory"
          />
        </div>
      </el-card>

      <!-- Feedback Dialog -->
      <el-dialog v-model="showFeedbackDialog" title="查询反馈" width="400px">
        <el-form :model="feedbackForm" label-width="80px">
          <el-form-item label="查询结果">
            <el-radio-group v-model="feedbackForm.isCorrect">
              <el-radio :label="true">正确</el-radio>
              <el-radio :label="false">错误</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="!feedbackForm.isCorrect" label="纠正SQL">
            <el-input v-model="feedbackForm.correctedSql" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="评分">
            <el-rate v-model="feedbackForm.rating" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showFeedbackDialog = false">取消</el-button>
          <el-button type="primary" @click="submitFeedback">提交</el-button>
        </template>
      </el-dialog>
    </el-main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useQueryStore, type QueryHistoryItem } from '@/stores/query'

const router = useRouter()
const queryStore = useQueryStore()

const currentPage = ref(1)
const total = ref(0)
const showFeedbackDialog = ref(false)
const selectedHistoryItem = ref<QueryHistoryItem | null>(null)

const feedbackForm = reactive({
  isCorrect: true,
  correctedSql: '',
  rating: 5,
})

onMounted(() => {
  loadHistory()
})

async function loadHistory() {
  const offset = (currentPage.value - 1) * 20
  await queryStore.fetchHistory(20, offset)
  total.value = queryStore.history.length + offset
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getStatusType(status: string) {
  switch (status) {
    case 'success':
      return 'success'
    case 'failed':
      return 'danger'
    case 'pending':
      return 'warning'
    default:
      return 'info'
  }
}

function showFeedback(item: QueryHistoryItem) {
  selectedHistoryItem.value = item
  feedbackForm.isCorrect = true
  feedbackForm.correctedSql = ''
  feedbackForm.rating = 5
  showFeedbackDialog.value = true
}

async function submitFeedback() {
  if (!selectedHistoryItem.value) return

  await queryStore.feedback(
    selectedHistoryItem.value.id,
    feedbackForm.isCorrect,
    feedbackForm.rating,
    feedbackForm.isCorrect ? undefined : feedbackForm.correctedSql
  )

  ElMessage.success('反馈已提交')
  showFeedbackDialog.value = false
}
</script>

<style scoped>
.history-container {
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

.sql-preview {
  display: inline-block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: monospace;
  font-size: 12px;
  cursor: pointer;
}
</style>
