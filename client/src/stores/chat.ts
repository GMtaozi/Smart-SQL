import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export interface Message {
  role: 'user' | 'assistant'
  content?: string
  sql?: string
  result?: any[]
  columns?: string[]
  rowCount?: number
  executionTime?: number
  error?: string
  viewMode?: 'table' | 'card' | 'chart'
  chartType?: 'bar' | 'pie' | 'line'
  xAxis?: string
  yAxis?: string
}

const STORAGE_KEY = 'sqlbot_chat'

// 从 localStorage 加载数据
function loadFromStorage() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const data = JSON.parse(stored)
      return {
        messages: data.messages || [],
        selectedDatasourceId: data.selectedDatasourceId || null,
        hiddenMessages: data.hiddenMessages || [],
        isScreenCleared: data.isScreenCleared || false,
      }
    }
  } catch (e) {
    console.warn('Failed to load chat from storage:', e)
  }
  return { messages: [], selectedDatasourceId: null, hiddenMessages: [], isScreenCleared: false }
}

// 保存数据到 localStorage
function saveToStorage(messages: Message[], selectedDatasourceId: number | null, hiddenMessages: Message[] = [], isScreenCleared: boolean = false) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      messages,
      selectedDatasourceId,
      hiddenMessages,
      isScreenCleared,
    }))
  } catch (e) {
    console.warn('Failed to save chat to storage:', e)
  }
}

export const useChatStore = defineStore('chat', () => {
  // 从 localStorage 加载初始数据
  const initialData = loadFromStorage()

  // 持久化聊天记录
  const messages = ref<Message[]>(initialData.messages)
  const selectedDatasourceId = ref<number | null>(initialData.selectedDatasourceId)

  // 是否正在生成 SQL
  const generating = ref(false)
  // 是否正在执行查询
  const executing = ref(false)

  // 计算属性：是否有历史消息
  const hasMessages = computed(() => messages.value.length > 0)

  // 临时隐藏的消息（清屏用，不删除历史记录）
  const hiddenMessages = ref<Message[]>(initialData.hiddenMessages)

  // 是否处于清屏状态
  const isScreenCleared = ref(initialData.isScreenCleared)

  // 监听变化自动保存（包括清屏状态）
  watch(
    [messages, selectedDatasourceId, hiddenMessages, isScreenCleared],
    () => {
      saveToStorage(messages.value, selectedDatasourceId.value, hiddenMessages.value, isScreenCleared.value)
    },
    { deep: true }
  )

  // 添加用户消息
  function addUserMessage(content: string) {
    // 清屏后发送新消息时，清除隐藏的历史记录，开始新对话
    if (isScreenCleared.value) {
      hiddenMessages.value = []
      isScreenCleared.value = false
    }
    messages.value.push({
      role: 'user',
      content,
    })
  }

  // 添加助手消息
  function addAssistantMessage(data: Partial<Message>) {
    messages.value.push({
      role: 'assistant',
      sql: data.sql,
      viewMode: data.viewMode || 'table',
      chartType: data.chartType || 'bar',
    })
  }

  // 更新助手消息（用于更新查询结果等）
  function updateAssistantMessage(index: number, data: Partial<Message>) {
    if (index >= 0 && index < messages.value.length) {
      const msg = messages.value[index]
      Object.assign(msg, data)
    }
  }

  // 获取最后一条助手消息的索引
  function getLastAssistantIndex(): number {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      if (messages.value[i].role === 'assistant') {
        return i
      }
    }
    return -1
  }

  // 清除所有消息
  function clearMessages() {
    messages.value = []
    hiddenMessages.value = []
    isScreenCleared.value = false
  }

  // 清屏：临时隐藏所有消息，但保留历史记录
  function clearScreen() {
    console.log('[DEBUG] clearScreen called, messages length:', messages.value.length)
    // 保存当前消息到隐藏列表
    if (messages.value.length > 0) {
      hiddenMessages.value = [...messages.value]
      messages.value = []
    }
    // 设置清屏状态
    isScreenCleared.value = true
    console.log('[DEBUG] after clearScreen, isScreenCleared:', isScreenCleared.value, 'hiddenMessages length:', hiddenMessages.value.length)
  }

  // 恢复显示隐藏的消息
  function restoreScreen() {
    console.log('[DEBUG] restoreScreen called, hiddenMessages length:', hiddenMessages.value.length)
    if (hiddenMessages.value.length > 0) {
      messages.value = [...hiddenMessages.value]
      hiddenMessages.value = []
      isScreenCleared.value = false
      console.log('[DEBUG] after restoreScreen, messages length:', messages.value.length)
    } else {
      // 如果没有隐藏消息，重置清屏状态
      isScreenCleared.value = false
    }
  }

  // 设置选中的数据源
  function setDatasource(id: number | null) {
    selectedDatasourceId.value = id
  }

  // 设置生成状态
  function setGenerating(value: boolean) {
    generating.value = value
  }

  // 设置执行状态
  function setExecuting(value: boolean) {
    executing.value = value
  }

  return {
    messages,
    selectedDatasourceId,
    generating,
    executing,
    hasMessages,
    hiddenMessages,
    isScreenCleared,
    addUserMessage,
    addAssistantMessage,
    updateAssistantMessage,
    getLastAssistantIndex,
    clearMessages,
    clearScreen,
    restoreScreen,
    setDatasource,
    setGenerating,
    setExecuting,
  }
})
