<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { login as loginApi, register as registerApi } from '@/api/auth'
import { useUserStore } from '@/store/userStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const mode = ref('login')
const loading = ref(false)

const form = reactive({
  userId: '',
  userName: '',
  password: '',
  confirmPassword: '',
  role: 'student',
})

const isRegister = computed(() => mode.value === 'register')
const isTeacherLogin = computed(() => !isRegister.value && form.role === 'teacher')
const submitText = computed(() => {
  if (isRegister.value) return '注册账号并进入'
  return isTeacherLogin.value ? '教师登录' : '学生登录'
})
const accountPlaceholder = computed(() => (isTeacherLogin.value ? '请输入教师账号' : '请输入学生账号'))
const passwordPlaceholder = '请输入密码'

const validateConfirmPassword = (_rule, value, callback) => {
  if (!isRegister.value) return callback()
  if (!value) return callback(new Error('请再次输入密码'))
  if (value !== form.password) return callback(new Error('两次输入的密码不一致'))
  callback()
}

const rules = {
  userId: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { min: 2, max: 64, message: '账号长度为 2-64 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
}

const switchMode = (nextMode) => {
  mode.value = nextMode
  if (nextMode === 'register') form.role = 'student'
  formRef.value?.clearValidate()
}

const switchLoginRole = (role) => {
  form.role = role
  formRef.value?.clearValidate()
}

const normalizeReturnUrl = (value) => {
  if (Array.isArray(value)) return normalizeReturnUrl(value[0])
  if (typeof value !== 'string') return ''
  if (!value.startsWith('/') || value.startsWith('/login')) return ''
  return value
}

const getRoleHomePath = (role) => (role === 'teacher' ? '/pc/teacher/upload' : '/pc/home')

const persistSession = (data) => {
  const token = data?.authToken || ''
  const userInfo = data?.userInfo || {}
  userStore.login(userInfo, token)
  return userInfo
}

const submit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()

  loading.value = true
  try {
    const payload = {
      userId: form.userId,
      userName: form.userName,
      password: form.password,
      role: isRegister.value ? 'student' : form.role,
    }
    const data = isRegister.value ? await registerApi(payload) : await loginApi(payload)
    const userInfo = persistSession(data)
    ElMessage.success(isRegister.value ? '注册成功' : '登录成功')
    router.replace(normalizeReturnUrl(route.query.returnUrl) || getRoleHomePath(userInfo.role))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <header class="auth-header">
      <span class="logo-mark">知</span>
      <span class="logo-name">知微智课</span>
      <span class="logo-tag">课程学习与备课入口</span>
    </header>

    <section :class="['auth-card', { 'is-register': isRegister }]">
      <div class="auth-heading">
        <h2>{{ isRegister ? '创建学生账号' : '欢迎回来' }}</h2>
        <p>{{ isRegister ? '注册后进入学生学习空间。教师账号由系统统一分配。' : '选择身份入口，进入对应的学习或教学工作台。' }}</p>
      </div>

      <div class="mode-switch" role="tablist" aria-label="登录注册切换">
        <button type="button" :class="{ active: mode === 'login' }" @click="switchMode('login')">
          登录
        </button>
        <button type="button" :class="{ active: mode === 'register' }" @click="switchMode('register')">
          学生注册
        </button>
      </div>

      <div v-if="!isRegister" class="role-field">
        <span>登录身份</span>
        <div class="role-grid">
          <button type="button" :class="{ active: form.role === 'student' }" @click="switchLoginRole('student')">
            学生
          </button>
          <button type="button" :class="{ active: form.role === 'teacher' }" @click="switchLoginRole('teacher')">
            教师
          </button>
        </div>
      </div>

      <el-form ref="formRef" class="auth-form" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="账号" prop="userId">
          <el-input v-model.trim="form.userId" :placeholder="accountPlaceholder" size="large" clearable>
            <template #prefix>
              <el-icon>
                <User />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="isRegister" label="显示名称">
          <el-input v-model.trim="form.userName" placeholder="可选，默认使用账号" size="large" clearable />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" :placeholder="passwordPlaceholder" size="large"
            show-password>
            <template #prefix>
              <el-icon>
                <Lock />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="isRegister" label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" size="large" show-password>
            <template #prefix>
              <el-icon>
                <Lock />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>


        <button class="submit-button" type="button" :disabled="loading" @click="submit">
          <span v-if="!loading" class="btn-content">
            <span>{{ submitText }}</span>
            <span class="btn-arrow">→</span>
          </span>
          <span v-else class="btn-spinner">
            <span class="spinner-ring" />处理中...
          </span>
        </button>
      </el-form>
    </section>

    <footer class="auth-footer">
      智能课程生成 · 互动答疑 · 学情洞察
    </footer>
  </main>
</template>

<style scoped>
.auth-page {
  box-sizing: border-box;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 32px 20px;
  overflow-y: auto;
  font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background:
    linear-gradient(180deg, rgba(13, 148, 136, 0.07), rgba(246, 248, 250, 0) 34%),
    #f6f8fa;
}

.auth-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  animation: fadeUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.logo-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #0d9488;
  color: #fff;
  font-size: 15px;
  font-weight: 800;
  box-shadow: 0 8px 22px rgba(13, 148, 136, 0.22);
}

.logo-name {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: 0;
}

.logo-tag {
  margin-left: 2px;
  padding-left: 10px;
  border-left: 1px solid #dbe3ec;
  font-size: 11px;
  color: #94a3b8;
  letter-spacing: 0;
}

.auth-card {
  box-sizing: border-box;
  width: 100%;
  max-width: 408px;
  min-height: 544px;
  display: flex;
  flex-direction: column;
  padding: 32px 36px 30px;
  border-radius: 8px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.035),
    0 20px 60px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(16px);
  animation: fadeUp 0.6s 0.06s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.auth-card.is-register {
  min-height: 560px;
}

.auth-heading {
  flex-shrink: 0;
  margin-bottom: 22px;
}

.auth-heading h2 {
  margin: 0 0 7px;
  font-size: 23px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: 0;
}

.auth-heading p {
  margin: 0;
  font-size: 13px;
  color: #8a99aa;
  line-height: 1.6;
}

.mode-switch {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px;
  padding: 3px;
  margin-bottom: 18px;
  border-radius: 8px;
  background: #f1f5f9;
  border: 1px solid #e8edf3;
}

.mode-switch button {
  all: unset;
  height: 34px;
  border-radius: 6px;
  text-align: center;
  font-size: 13.5px;
  font-weight: 600;
  color: #94a3b8;
  cursor: pointer;
  transition: background 0.14s, color 0.14s, box-shadow 0.14s;
}

.mode-switch button.active {
  background: #fff;
  color: #0f172a;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.09);
}

.role-field {
  display: grid;
  gap: 7px;
  margin-bottom: 10px;
}

.role-field>span {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0;
}

.role-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.role-grid button {
  all: unset;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 500;
  color: #64748b;
  border: 1px solid #e2e8f0;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s, box-shadow 0.15s;
}

.role-grid button:hover {
  border-color: #99d8d0;
  color: #0d9488;
  background: #f0fdfa;
}

.role-grid button.active {
  border-color: #0d9488;
  background: #0d9488;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.22);
}

.register-note {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.auth-form {
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.el-form-item) {
  margin-bottom: 15px;
}

.auth-card.is-register :deep(.el-form-item) {
  margin-bottom: 14px;
}

:deep(.el-form-item__label) {
  padding-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0;
  line-height: 1;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  transition: box-shadow 0.15s, background 0.15s;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #b7c4d1 inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.42) inset;
}

:deep(.el-input__inner) {
  font-size: 14px;
  color: #1e293b;
}

.submit-button {
  all: unset;
  box-sizing: border-box;
  width: 100%;
  height: 44px;
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 14.5px;
  font-weight: 700;
  color: #fff;
  background: #0d9488;
  box-shadow: 0 8px 22px rgba(13, 148, 136, 0.24);
  cursor: pointer;
  transition: background 0.16s, transform 0.16s, box-shadow 0.16s;
}

.submit-button:hover:not(:disabled) {
  background: #0f766e;
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(13, 148, 136, 0.3);
}

.submit-button:active:not(:disabled) {
  transform: translateY(0);
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-content {
  display: flex;
  align-items: center;
  gap: 7px;
}

.btn-arrow {
  font-size: 15px;
  transition: transform 0.16s;
}

.submit-button:hover .btn-arrow {
  transform: translateX(3px);
}

.btn-spinner {
  display: flex;
  align-items: center;
  gap: 9px;
}

.spinner-ring {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  animation: spin 0.7s linear infinite;
}

.auth-footer {
  flex-shrink: 0;
  font-size: 12px;
  color: #a9b6c4;
  letter-spacing: 0;
  animation: fadeUp 0.6s 0.14s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-height: 720px) {
  .auth-page {
    justify-content: flex-start;
    padding-top: 24px;
    padding-bottom: 24px;
  }

  .auth-footer {
    display: none;
  }
}

@media (max-width: 480px) {
  .auth-page {
    justify-content: flex-start;
    padding: 32px 18px;
  }

  .auth-card {
    min-height: 520px;
    padding: 28px 22px 24px;
  }

  .auth-card.is-register {
    min-height: 540px;
  }

  .logo-tag {
    display: none;
  }
}

/* Impeccable quieter pass: make auth feel like a real campus product entry. */
.auth-page {
  display: grid;
  grid-template-columns: minmax(280px, 420px) minmax(360px, 440px);
  align-content: center;
  justify-content: center;
  column-gap: 72px;
  row-gap: 20px;
  padding: 48px 32px;
  background: #f5f6f8;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.auth-header {
  align-self: center;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 10px 12px;
  padding: 0;
  animation: none;
}

.auth-header::after {
  content: "面向教师备课、课程发布、学生学习与答疑记录的本地开发入口。";
  grid-column: 2;
  max-width: 30ch;
  color: #6b7785;
  font-size: 13px;
  line-height: 1.7;
}

.logo-mark {
  width: 42px;
  height: 42px;
  border: 1px solid #cfd8ea;
  border-radius: 6px;
  background: #eef3ff;
  color: #245bdb;
  box-shadow: none;
  font-weight: 600;
}

.logo-name {
  align-self: end;
  color: #1d2129;
  font-size: 22px;
  font-weight: 600;
}

.logo-tag {
  grid-column: 2;
  margin: 0;
  padding: 0;
  border: 0;
  color: #6b7785;
  font-size: 13px;
}

.auth-card {
  max-width: none;
  min-height: auto;
  padding: 30px 32px 28px;
  border-color: #dfe1e6;
  border-radius: 6px;
  background: #fffffe;
  box-shadow: 0 1px 3px rgba(29, 33, 41, 0.06);
  backdrop-filter: none;
  animation: none;
}

.auth-card.is-register {
  min-height: auto;
}

.auth-heading h2 {
  color: #1d2129;
  font-size: 22px;
  font-weight: 600;
}

.auth-heading p {
  color: #6b7785;
}

.mode-switch {
  border-color: #dfe1e6;
  background: #f7f8fa;
}

.mode-switch button {
  color: #6b7785;
  font-weight: 500;
}

.mode-switch button.active {
  color: #1d2129;
  box-shadow: none;
}

.role-field > span,
:deep(.el-form-item__label) {
  color: #4e5969;
  font-weight: 500;
}

.role-grid button {
  border-color: #dfe1e6;
  color: #4e5969;
}

.role-grid button:hover {
  border-color: #b9c9f7;
  color: #245bdb;
  background: #f7f9ff;
}

.role-grid button.active {
  border-color: #3370ff;
  background: #3370ff;
  box-shadow: none;
}

:deep(.el-input__wrapper) {
  border-radius: 6px;
  box-shadow: 0 0 0 1px #dfe1e6 inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c8d2e6 inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #3370ff inset;
}

.submit-button {
  border-radius: 6px;
  background: #3370ff;
  box-shadow: none;
  font-weight: 600;
}

.submit-button:hover:not(:disabled) {
  background: #245bdb;
  transform: none;
  box-shadow: none;
}

.submit-button:hover .btn-arrow {
  transform: none;
}

.auth-footer {
  display: none;
}

@media (max-width: 860px) {
  .auth-page {
    grid-template-columns: minmax(0, 440px);
    justify-content: center;
    padding: 32px 18px;
  }

  .auth-header {
    align-self: auto;
  }

  .auth-footer {
    grid-column: auto;
  }
}
</style>
