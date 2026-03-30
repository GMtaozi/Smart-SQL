<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2>SQLbot 登录</h2>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-form-item v-if="isRegisterMode" label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱（可选）" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            {{ isRegisterMode ? '注册' : '登录' }}
          </el-button>
          <el-button text @click="isRegisterMode = !isRegisterMode">
            {{ isRegisterMode ? '返回登录' : '没有账号？去注册' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)
const isRegisterMode = ref(false)

const form = reactive({
  username: '',
  password: '',
  email: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleSubmit() {
  await formRef.value?.validate()

  loading.value = true
  try {
    if (isRegisterMode.value) {
      await authStore.registerAction(form.username, form.password, form.email)
      ElMessage.success('注册成功，请登录')
      isRegisterMode.value = false
    } else {
      await authStore.loginAction(form.username, form.password)
      ElMessage.success('登录成功')
      router.push('/')
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
}

.login-card h2 {
  text-align: center;
  margin: 0;
  color: #333;
}
</style>
