<template>
  <el-select
    v-model="selectedId"
    placeholder="选择数据源"
    :loading="loading"
    @change="handleChange"
  >
    <el-option
      v-for="ds in datasources"
      :key="ds.id"
      :label="ds.name"
      :value="ds.id"
    />
  </el-select>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getDatasources } from '@/api/schema'
import type { Datasource } from '@/types'

const props = defineProps<{
  modelValue?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | undefined]
}>()

const selectedId = ref<number | undefined>(props.modelValue)
const datasources = ref<Datasource[]>([])
const loading = ref(false)

watch(() => props.modelValue, (val) => {
  selectedId.value = val
})

onMounted(async () => {
  loading.value = true
  try {
    datasources.value = await getDatasources()
    if (!selectedId.value && datasources.value.length > 0) {
      selectedId.value = datasources.value[0].id
      emit('update:modelValue', selectedId.value)
    }
  } finally {
    loading.value = false
  }
})

function handleChange(val: number) {
  emit('update:modelValue', val)
}
</script>
