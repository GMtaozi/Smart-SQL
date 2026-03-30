<template>
  <div class="ai-model-page">
    <div class="page-header">
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加模型
      </el-button>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <el-col :span="8" v-for="model in models" :key="model.id">
        <el-card class="model-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <div>
                <span class="model-name">{{ model.name }}</span>
                <el-tag v-if="model.is_default" type="success" size="small">默认</el-tag>
              </div>
              <el-dropdown @command="(cmd: string) => handleCommand(cmd, model)">
                <el-button text>
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="default">
                      <el-icon><Check /></el-icon>
                      设为默认
                    </el-dropdown-item>
                    <el-dropdown-item command="test">
                      <el-icon><VideoPlay /></el-icon>
                      测试连接
                    </el-dropdown-item>
                    <el-dropdown-item command="edit">
                      <el-icon><Edit /></el-icon>
                      编辑
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <el-icon><Delete /></el-icon>
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>

          <div class="model-info">
            <div class="info-item">
              <span class="label">供应商:</span>
              <span class="value">{{ model.supplier_name }}</span>
            </div>
            <div class="info-item">
              <span class="label">模型:</span>
              <span class="value">{{ model.base_model }}</span>
            </div>
            <div class="info-item">
              <span class="label">API Key:</span>
              <span class="value">{{ model.api_key }}</span>
            </div>
            <div class="info-item" v-if="model.api_domain">
              <span class="label">Endpoint:</span>
              <span class="value domain">{{ model.api_domain }}</span>
            </div>
          </div>

          <div class="card-footer">
            <el-tag :type="model.enabled ? 'success' : 'info'" size="small">
              {{ model.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && models.length === 0" description="暂无 AI 模型，请添加">
      <el-button type="primary" @click="showAddDialog">添加模型</el-button>
    </el-empty>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模型' : '添加模型'"
      width="650px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: OpenAI GPT-4" />
        </el-form-item>

        <el-form-item label="供应商" prop="supplier">
          <el-select v-model="form.supplier" placeholder="选择供应商" @change="handleSupplierChange">
            <el-option
              v-for="supplier in supplierList"
              :key="supplier.value"
              :label="supplier.label"
              :value="supplier.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="模型名称" prop="base_model">
          <el-select
            v-model="form.base_model"
            placeholder="选择或输入模型"
            filterable
            allow-create
            default-first-option
          >
            <el-option
              v-for="model in availableModels"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="输入 API Key" />
        </el-form-item>

        <el-form-item label="API 地址">
          <el-input v-model="form.api_domain" :placeholder="defaultApiDomain || '留空使用默认值'" />
          <div class="form-tip">默认: {{ defaultApiDomain || '无' }}</div>
        </el-form-item>

        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button @click="handleTestConnection" :loading="testing">
          <el-icon><Connection /></el-icon>
          测试连接
        </el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Test Dialog -->
    <el-dialog v-model="testDialogVisible" title="测试连接" width="400px">
      <div v-if="testResult">
        <el-result
          :icon="testResult.success ? 'success' : 'error'"
          :title="testResult.success ? '连接成功' : '连接失败'"
        >
          <template #sub-title>
            <p>{{ testResult.message }}</p>
          </template>
        </el-result>
      </div>
      <div v-else>
        <p>正在测试连接...</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus, MoreFilled, Check, Edit, Delete, VideoPlay, Connection } from '@element-plus/icons-vue'
import { aiModelApi, AIModel, AIModelForm } from '@/api/aiModel'

const loading = ref(false)
const submitting = ref(false)
const testing = ref(false)
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const models = ref<AIModel[]>([])
const testResult = ref<{ success: boolean; message: string } | null>(null)

const formRef = ref<FormInstance>()

const form = reactive<AIModelForm>({
  name: '',
  supplier: 'openai',
  model_type: 0,
  base_model: '',
  api_key: '',
  api_domain: '',
  is_default: false,
  enabled: true,
})

const rules = computed<FormRules>(() => ({
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  supplier: [{ required: true, message: '请选择供应商', trigger: 'change' }],
  base_model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  // 编辑时 API Key 非必填（允许保持现有密钥）
  api_key: [{ required: !isEdit.value, message: '请输入 API Key', trigger: 'blur' }],
}))

// 供应商列表
const supplierList = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'zhipu', label: '智谱AI' },
  { value: 'qianfan', label: '百度千帆' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'tencent', label: '腾讯混元' },
  { value: 'xunfei', label: '讯飞星火' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'kimi', label: 'Kimi/Moonshot' },
  { value: 'dashscope', label: '阿里云百炼' },
  { value: 'volcengine', label: '火山引擎' },
  { value: 'minimax', label: 'MiniMax' },
  { value: 'custom', label: '自定义/私有部署' },
]

// 供应商配置：默认 API Domain 和模型列表
const supplierConfig: Record<string, { api_domain: string; models: string[] }> = {
  openai: {
    api_domain: 'https://api.openai.com/v1',
    models: ['gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4o', 'gpt-4o-mini', 'chatgpt-4o-latest', 'o4-mini', 'o3', 'o3-mini', 'o1', 'o1-pro', 'o1-mini'],
  },
  zhipu: {
    api_domain: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-4', 'glm-4-flash', 'glm-4-plus', 'glm-3-turbo'],
  },
  qianfan: {
    api_domain: 'https://qianfan.baidubce.com/v2/',
    models: ['ernie-4.0-8k', 'ernie-4.0-32k', 'ernie-4.0-turbo-8k', 'ernie-3.5-8k', 'ernie-3.5-32k', 'ernie-speed-8k', 'ernie-speed-32k', 'ernie-lite-8k'],
  },
  deepseek: {
    api_domain: 'https://api.deepseek.com',
    models: ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner'],
  },
  tencent: {
    api_domain: 'https://api.hunyuan.cloud.tencent.com/v1/',
    models: ['hunyuan-turbos-latest', 'hunyuan-standard-256K', 'hunyuan-standard', 'hunyuan-lite'],
  },
  xunfei: {
    api_domain: 'https://spark-api-open.xf-yun.com/v3.5/',
    models: ['4.0Ultra', 'x1', 'generalv3.5', 'generalv3', 'lite'],
  },
  gemini: {
    api_domain: 'https://generativelanguage.googleapis.com/v1beta/openai/',
    models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.0-flash', 'gemini-2.0-flash-lite'],
  },
  kimi: {
    api_domain: 'https://api.moonshot.cn/v1',
    models: ['kimi-k2-0711-preview', 'kimi-k2-turbo-preview', 'moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k', 'moonshot-v1-auto', 'moonshot-v1-8k-vision-preview'],
  },
  dashscope: {
    api_domain: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen3-coder-plus', 'qwen3-coder-flash', 'qwen-plus', 'qwen-max', 'qwen-max-latest', 'qwen-turbo', 'qwen-turbo-latest', 'qwen-long', 'qwen-long-latest'],
  },
  volcengine: {
    api_domain: 'https://ark.cn-beijing.volces.com/api/v3',
    models: ['doubao-seed-1-6-250615', 'doubao-seed-1-6-flash-250715', 'doubao-1-5-pro-32k-character-250715', 'kimi-k2-250711', 'deepseek-v3-250324', 'deepseek-r1'],
  },
  minimax: {
    api_domain: 'https://api.minimax.io/v1',
    models: ['MiniMax-M2.7', 'MiniMax-M2.5', 'MiniMax-M2.5-highspeed'],
  },
  custom: {
    api_domain: '',
    models: [],
  },
}

const defaultApiDomain = computed(() => supplierConfig[form.supplier]?.api_domain || '')
const availableModels = computed(() => supplierConfig[form.supplier]?.models || [])

const loadModels = async () => {
  loading.value = true
  try {
    const res = await aiModelApi.list()
    models.value = res.data
  } catch (error) {
    ElMessage.error('加载模型列表失败')
  } finally {
    loading.value = false
  }
}

const handleSupplierChange = (supplier: string) => {
  const config = supplierConfig[supplier]
  if (config && config.models.length > 0) {
    form.base_model = config.models[0]
  } else {
    form.base_model = ''
  }
  // 自动填充 API Domain
  if (config && config.api_domain) {
    form.api_domain = config.api_domain
  }
}

const showAddDialog = () => {
  isEdit.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

const showEditDialog = (model: AIModel) => {
  isEdit.value = true
  editingId.value = model.id
  form.name = model.name
  form.supplier = model.supplier
  form.model_type = model.model_type
  form.base_model = model.base_model
  form.api_key = ''
  form.api_domain = model.api_domain || ''
  form.is_default = model.is_default
  form.enabled = model.enabled
  dialogVisible.value = true
}

const resetForm = () => {
  form.name = ''
  form.supplier = 'openai'
  form.model_type = 0
  form.base_model = 'gpt-4o-mini'
  form.api_key = ''
  form.api_domain = supplierConfig['openai'].api_domain
  form.is_default = models.value.length === 0
  form.enabled = true
}

const handleTestConnection = async () => {
  if (!form.api_key) {
    ElMessage.warning('请先输入 API Key')
    return
  }
  testing.value = true
  testDialogVisible.value = true
  testResult.value = null
  try {
    const res = await aiModelApi.test({
      api_key: form.api_key,
      model: form.base_model,
      supplier: form.supplier,
      api_domain: form.api_domain || undefined,
    })
    testResult.value = res.data
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: error.response?.data?.message || '测试连接失败',
    }
  } finally {
    testing.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (isEdit.value && editingId.value) {
      await aiModelApi.update(editingId.value, form)
      ElMessage.success('模型更新成功')
    } else {
      await aiModelApi.create(form)
      ElMessage.success('模型添加成功')
    }

    dialogVisible.value = false
    loadModels()
  } catch (error: any) {
    if (!error.errors) {
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleCommand = async (command: string, model: AIModel) => {
  switch (command) {
    case 'default':
      try {
        await aiModelApi.setDefault(model.id)
        ElMessage.success('已设为默认模型')
        loadModels()
      } catch (error) {
        ElMessage.error('设置失败')
      }
      break
    case 'test':
      testDialogVisible.value = true
      testResult.value = null
      try {
        const res = await aiModelApi.test({
          api_key: model.api_key || 'test',
          model: model.base_model,
          supplier: model.supplier,
          api_domain: model.api_domain,
        })
        testResult.value = res.data
      } catch (error: any) {
        testResult.value = {
          success: false,
          message: error.response?.data?.message || '连接失败',
        }
      }
      break
    case 'edit':
      showEditDialog(model)
      break
    case 'delete':
      try {
        await ElMessageBox.confirm('确定要删除这个模型吗？', '提示', {
          type: 'warning',
        })
        await aiModelApi.delete(model.id)
        ElMessage.success('删除成功')
        loadModels()
      } catch (error: any) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
      break
  }
}

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.ai-model-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.model-card {
  margin-bottom: 20px;
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.model-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-name {
  font-size: 16px;
  font-weight: 600;
  margin-right: 8px;
}

.model-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
  font-size: 14px;
}

.info-item .label {
  color: #909399;
  width: 70px;
  flex-shrink: 0;
}

.info-item .value {
  color: #303133;
  word-break: break-all;
}

.info-item .domain {
  font-size: 12px;
  color: #606266;
}

.card-footer {
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
