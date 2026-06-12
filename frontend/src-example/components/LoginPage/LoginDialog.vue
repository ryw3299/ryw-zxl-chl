<script setup>
import { onMounted, reactive, ref } from "vue";
import { Lock, User, School } from "@element-plus/icons-vue";
import { useAuth } from "@/assets/static/js/useAuth"
import { schools } from "@/assets/static/js/resources.js";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";

const windowWidth = ref(window.innerWidth)
const windowHeight = ref(window.innerHeight)
const rescaleElement = () => {
  windowWidth.value = window.innerWidth
  windowHeight.value = window.innerHeight
}

const { login } = useAuth()
const loginForm = reactive({
  school: schools[0]?.label || '演示学校',
  id: '',
  password: ''
})
const emit = defineEmits(['handleClose','showRegister'])
const activeTab = ref('student')
const helpDialVis = ref(false)
const router = useRouter()

const validForm = () => {
  if (loginForm.id === '' || loginForm.password === '') {
    ElMessage({
      message: '请输入账号和密码',
      type: 'warning',
      duration: 2000
    })
    return false
  }
  return true
}

const demoUsers = {
  student: {
    id: '123',
    password: '123',
    name: '演示学生',
    email: 'student@example.local',
    ident: '123',
    enrollment: '2026',
  },
  teacher: {
    id: '123',
    password: '123',
    name: '演示教师',
    email: 'teacher@example.local',
    ident: '123',
    enrollment: '',
  },
}

const handleLogin = () => {
  if (!validForm()) return

  const demoUser = demoUsers[activeTab.value]
  if (!demoUser || loginForm.id !== demoUser.id || loginForm.password !== demoUser.password) {
    ElMessage({
      message: '演示账号或密码错误',
      type: 'error',
      duration: 2000
    })
    return
  }

  login({
    school: loginForm.school || '演示学校',
    id: demoUser.id,
    role: activeTab.value,
    name: demoUser.name,
    email: demoUser.email,
    ident: demoUser.ident,
    enrollment: demoUser.enrollment,
  })

  ElMessage({
    message: '登录成功',
    type: 'success',
    duration: 1200
  })

  if (activeTab.value === 'student') {
    router.push('/portal')
  } else if (activeTab.value === 'teacher') {
    router.push('/teaching/portal')
  }
};


onMounted(() => {
  window.addEventListener('resize', () => {
    rescaleElement()
  })
})
</script>

<template>
  <el-dialog
      align-center
      width="500"
      :before-close="emit('handleClose')"
  >
    <div id="login-tab-container">
      <el-tabs v-model="activeTab" style="margin-top: 72px">
        <el-tab-pane label="学生" name="student">
          <div class="Center-Flex" style="margin-top: 46px">
            <el-form :model="loginForm">
                  <el-form-item>
                    <el-select
                        :prefix-icon="School"
                        class="loginInput"
                        placeholder="请输入或选择你的学校"
                        filterable
                        v-model="loginForm.school"
                        size="large"
                    >
                      <el-option
                          v-for="item in schools"
                          :key="item.label"
                          :label="item.label"
                          :value="item.label"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-input
                        :prefix-icon="User"
                        class="loginInput"
                        placeholder="这里是你的学号"
                        v-model="loginForm.id"
                        size="large">
                    </el-input>
                  </el-form-item>
                  <el-form-item>
                    <el-input
                        :prefix-icon="Lock"
                        class="loginInput"
                        placeholder="还有你的密码"
                        v-model="loginForm.password"
                        size="large"
                        show-password>
                    </el-input>
                  </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="教师" name="teacher">
          <div class="Center-Flex" style="margin-top: 46px">
            <el-form :model="loginForm">
              <el-form-item>
                <el-select
                    :prefix-icon="School"
                    class="loginInput"
                    placeholder="请输入或选择您所在的学校（工作单位）"
                    filterable
                    v-model="loginForm.school"
                    size="large"
                >
                  <el-option
                      v-for="item in schools"
                      :key="item.label"
                      :label="item.label"
                      :value="item.label"
                  />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-input
                    :prefix-icon="User"
                    class="loginInput"
                    placeholder="请在此输入您的教工号"
                    v-model="loginForm.id"
                    size="large">
                </el-input>
              </el-form-item>

              <el-form-item>
                <el-input
                    :prefix-icon="Lock"
                    class="loginInput"
                    placeholder="请在此输入您的密码"
                    v-model="loginForm.password"
                    size="large"
                    show-password>
                </el-input>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>

      <el-text class="demo-account-hint">
        演示账号：学生 123 / 123，教师 123 / 123
      </el-text>

      <div class="Center-Flex">
        <el-button
            type="primary"
            class="loginButton"
            @click="handleLogin"
            size="large">
          登录</el-button>
      </div>
      <el-divider content-position="center" style="margin-top: 72px; margin-bottom: 72px">做有感情、有温度的教育</el-divider>
    </div>
    <div class="Center-Flex" style="margin-top: 0; margin-bottom: 32px">
      <el-text>
        如登录、注册遇到问题，请
      </el-text>
      <el-link type="primary" @click="helpDialVis = true">
        联系客服
      </el-link>
      <el-text>
        。
      </el-text>
    </div>
    <el-dialog
        title="联系客服"
        v-model="helpDialVis"
        align-center
        width="500"
    >
      <span>联络方式：tochus@163.com(电子邮箱)</span>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="helpDialVis = false">关闭</el-button>
          <el-button type="primary" @click="helpDialVis = false">
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<style scoped>
.loginInput {
  width: 400px;
  margin-bottom: 16px;
}
.loginButton {
  width: 400px;
  margin-top: 16px;
  margin-bottom: 18px;
}
.demo-account-hint {
  display: block;
  text-align: center;
  margin-top: 8px;
  color: var(--el-text-color-secondary);
}

#login-tab-container {
  margin: 12px;
}
</style>