<template>
  <div class="terminology-page">
    <div class="page-header">
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加术语
      </el-button>
    </div>

    <el-table :data="terminologies" v-loading="loading" stripe>
      <el-table-column prop="name" label="术语" min-width="120" />
      <el-table-column prop="term_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ getTermTypeName(row.term_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="synonyms" label="同义词" min-width="200" show-overflow-tooltip />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
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
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑术语' : '添加术语'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="术语" prop="name">
          <el-input v-model="form.name" placeholder="业务术语名称" />
        </el-form-item>

        <el-form-item label="类型" prop="term_type">
          <el-select v-model="form.term_type" placeholder="选择类型">
            <el-option v-for="type in termTypes" :key="type.value" :label="type.label" :value="type.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="同义词">
          <el-input v-model="form.synonyms" type="textarea" :rows="2" placeholder="同义词，用逗号分隔" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="术语描述或定义" />
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
import { terminologyApi, Terminology, TerminologyForm } from '@/api/terminology'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const terminologies = ref<Terminology[]>([])
const formRef = ref<FormInstance>()

const termTypes = [
  { value: 'GENERATE_SQL', label: 'SQL生成' },
  { value: 'ANALYSIS', label: '数据分析' },
  { value: 'PREDICT', label: '数据预测' },
]

const form = reactive<TerminologyForm>({
  name: '',
  term_type: 'GENERATE_SQL',
  synonyms: '',
  description: '',
  enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入术语', trigger: 'blur' }],
  term_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

const getTermTypeName = (type: string) => {
  return termTypes.find(t => t.value === type)?.label || type
}

const loadTerminologies = async () => {
  loading.value = true
  try {
    const res = await terminologyApi.list()
    terminologies.value = res.data
  } catch (error) {
    ElMessage.error('加载术语列表失败')
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

const handleEdit = (row: Terminology) => {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.term_type = row.term_type || 'GENERATE_SQL'
  form.synonyms = row.synonyms || ''
  form.description = row.description || ''
  form.enabled = row.enabled
  dialogVisible.value = true
}

const resetForm = () => {
  form.name = ''
  form.term_type = 'GENERATE_SQL'
  form.synonyms = ''
  form.description = ''
  form.enabled = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (isEdit.value && editingId.value) {
      await terminologyApi.update(editingId.value, form)
      ElMessage.success('术语更新成功')
    } else {
      await terminologyApi.create(form)
      ElMessage.success('术语添加成功')
    }

    dialogVisible.value = false
    loadTerminologies()
  } catch (error: any) {
    if (!error.errors) {
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: Terminology) => {
  try {
    await ElMessageBox.confirm('确定要删除这个术语吗？', '提示', { type: 'warning' })
    await terminologyApi.delete(row.id)
    ElMessage.success('删除成功')
    loadTerminologies()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadTerminologies()
})
</script>

<style scoped>
.terminology-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}
</style>
