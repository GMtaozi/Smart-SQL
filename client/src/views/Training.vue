<template>
  <div class="training-page">
    <div class="page-header">
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加训练数据
      </el-button>
    </div>

    <el-table :data="trainingData" v-loading="loading" stripe>
      <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="sql" label="SQL" min-width="250" show-overflow-tooltip>
        <template #default="{ row }">
          <code class="sql-preview">{{ truncateSql(row.sql) }}</code>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑训练数据' : '添加训练数据'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="问题" prop="question">
          <el-input v-model="form.question" type="textarea" :rows="2" placeholder="自然语言问题" />
        </el-form-item>

        <el-form-item label="SQL" prop="sql">
          <el-input v-model="form.sql" type="textarea" :rows="4" placeholder="对应的 SQL 查询" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="描述或备注" />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { trainingApi, TrainingData, TrainingForm } from '@/api/training'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const trainingData = ref<TrainingData[]>([])
const formRef = ref<FormInstance>()

const form = reactive<TrainingForm>({
  question: '',
  sql: '',
  description: '',
  enabled: true,
})

const rules: FormRules = {
  question: [{ required: true, message: '请输入问题', trigger: 'blur' }],
  sql: [{ required: true, message: '请输入 SQL', trigger: 'blur' }],
}

const truncateSql = (sql: string) => {
  if (sql.length > 100) {
    return sql.substring(0, 100) + '...'
  }
  return sql
}

const loadTrainingData = async () => {
  loading.value = true
  try {
    const res = await trainingApi.list()
    trainingData.value = res.data
  } catch (error) {
    ElMessage.error('加载训练数据失败')
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

const handleEdit = (row: TrainingData) => {
  isEdit.value = true
  editingId.value = row.id
  form.question = row.question
  form.sql = row.sql
  form.description = row.description || ''
  form.enabled = row.enabled
  dialogVisible.value = true
}

const resetForm = () => {
  form.question = ''
  form.sql = ''
  form.description = ''
  form.enabled = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (isEdit.value && editingId.value) {
      await trainingApi.update(editingId.value, form)
      ElMessage.success('训练数据更新成功')
    } else {
      await trainingApi.create(form)
      ElMessage.success('训练数据添加成功')
    }

    dialogVisible.value = false
    loadTrainingData()
  } catch (error: any) {
    if (!error.errors) {
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: TrainingData) => {
  try {
    await ElMessageBox.confirm('确定要删除这条训练数据吗？', '提示', { type: 'warning' })
    await trainingApi.delete(row.id)
    ElMessage.success('删除成功')
    loadTrainingData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadTrainingData()
})
</script>

<style scoped>
.training-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.sql-preview {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
