<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
          <rect x="2" y="2" width="36" height="36" rx="10" fill="#2563eb"/>
          <path d="M12 20L18 26L28 14" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h1 class="login-title">智学工坊</h1>
        <p class="login-tagline">AI赋能学习，成长看得见</p>
      </div>

      <div class="login-tabs">
        <el-radio-group v-model="mode" class="mode-switch">
          <el-radio-button value="login">登录</el-radio-button>
          <el-radio-button value="register">注册</el-radio-button>
        </el-radio-group>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" class="login-form" @submit.prevent="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" :placeholder="isRegister ? '请设置用户名' : '请输入用户名'" size="large" :prefix-icon="User" />
        </el-form-item>

        <el-form-item prop="email" v-if="isRegister">
          <el-input v-model="form.email" placeholder="邮箱（选填）" size="large" :prefix-icon="Message" />
        </el-form-item>

        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" :placeholder="isRegister ? '请设置密码（至少6位）' : '请输入密码'" size="large" :prefix-icon="Lock" show-password />
        </el-form-item>

        <el-form-item prop="confirmPassword" v-if="isRegister">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" size="large" :prefix-icon="Lock" show-password />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">
            {{ isRegister ? '注册并进入' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <p class="login-footer">智学工坊 · 让学习资源不再千篇一律</p>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Message, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref()
const mode = ref('login')
const loading = ref(false)

const form = reactive({ username: '', password: '', confirmPassword: '', email: '' })
const isRegister = computed(() => mode.value === 'register')

const validateConfirm = (_rule, value, callback) => {
  if (!isRegister.value) return callback()
  if (!value) return callback(new Error('请再次输入密码'))
  if (value !== form.password) return callback(new Error('两次输入的密码不一致'))
  callback()
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 64, message: '用户名长度 2-64 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [{ validator: validateConfirm, trigger: 'blur' }],
}

async function submit() {
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }
  loading.value = true
  try {
    if (isRegister.value) {
      await userStore.register(form.username, form.password, form.email)
      ElMessage.success('注册成功')
      router.push('/profile/init')
      return
    } else {
      await userStore.login(form.username, form.password)
    }
    router.push((route.query.returnUrl || '/dashboard'))
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 50%, #bfdbfe 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}
.login-page::before {
  content: '';
  position: absolute;
  top: -200px;
  right: -200px;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(37,99,235,0.03) 0%, transparent 70%);
  pointer-events: none;
}

.login-card {
  width: 420px;
  max-width: 100%;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(37,99,235,0.08);
  position: relative;
}

.login-brand {
  text-align: center;
  margin-bottom: 32px;
}
.login-brand svg { margin-bottom: 12px; }
.login-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.login-tagline {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.login-tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 28px;
}

.login-form { max-width: 340px; margin: 0 auto; }
.submit-btn { width: 100%; height: 44px; font-size: 1rem; }

.login-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 0.78rem;
  color: var(--text-muted);
}
</style>
