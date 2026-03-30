<template>
  <el-card class="result-card">
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span>查询结果</span>
        <div style="display: flex; gap: 16px; font-size: 12px; color: #909399;">
          <span>行数: {{ result.row_count }}</span>
          <span>耗时: {{ result.execution_time_ms.toFixed(0) }}ms</span>
        </div>
      </div>
    </template>

    <el-table :data="result.rows" stripe border max-height="500">
      <el-table-column
        v-for="col in result.columns"
        :key="col"
        :prop="col"
        :label="col"
        min-width="150"
        show-overflow-tooltip
      />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import type { QueryResult } from '@/stores/query'

defineProps<{
  result: QueryResult
}>()
</script>

<style scoped>
.result-card {
  margin-top: 16px;
}
</style>
