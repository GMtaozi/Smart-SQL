<template>
  <el-card class="sql-viewer-card">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span>生成的 SQL</span>
        <div>
          <el-tag v-for="table in usedTables" :key="table" size="small" style="margin-right: 8px;">
            {{ table }}
          </el-tag>
        </div>
      </div>
    </template>

    <div class="sql-code">
      <pre><code>{{ sql }}</code></pre>
    </div>

    <div style="margin-top: 16px; display: flex; gap: 12px;">
      <el-button type="primary" @click="handleExecute">
        执行查询
      </el-button>
      <el-button @click="handleCopy">
        <el-icon><document-copy /></el-icon>
        复制
      </el-button>
      <el-button text @click="emit('clear')">
        清除
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const props = defineProps<{
  sql: string
  usedTables: string[]
  datasourceId: number | null
}>()

const emit = defineEmits<{
  execute: [sql: string]
  clear: []
}>()

function handleExecute() {
  emit('execute', props.sql)
}

function handleCopy() {
  navigator.clipboard.writeText(props.sql)
  ElMessage.success('已复制到剪贴板')
}
</script>

<style scoped>
.sql-viewer-card {
  margin-bottom: 16px;
}

.sql-code {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 16px;
  overflow-x: auto;
}

.sql-code pre {
  margin: 0;
}

.sql-code code {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
