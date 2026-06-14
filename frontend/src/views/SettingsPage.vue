<template>
  <div class="settings-page">
    <section class="hero-card">
      <div>
        <p class="hero-label">账号与偏好</p>
        <h1>设置</h1>
        <p class="hero-desc">管理你的账号信息、学习偏好和提醒方式，让学习体验更贴合当前节奏。</p>
      </div>
      <el-button type="primary" @click="saveSettings">保存设置</el-button>
    </section>

    <section class="content-grid">
      <article class="surface-card">
        <div class="section-head">
          <h2>个人信息</h2>
        </div>
        <div class="form-grid">
          <label class="field">
            <span>用户名</span>
            <el-input v-model="form.username" />
          </label>
          <label class="field">
            <span>邮箱</span>
            <el-input v-model="form.email" />
          </label>
          <label class="field">
            <span>学习阶段</span>
            <el-select v-model="form.grade">
              <el-option label="初二" value="初二" />
              <el-option label="初三" value="初三" />
              <el-option label="高一" value="高一" />
            </el-select>
          </label>
          <label class="field">
            <span>目标方向</span>
            <el-select v-model="form.goal">
              <el-option label="提分" value="提分" />
              <el-option label="竞赛" value="竞赛" />
              <el-option label="项目实践" value="项目实践" />
            </el-select>
          </label>
        </div>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>学习偏好</h2>
        </div>
        <div class="preference-list">
          <div class="preference-item">
            <div>
              <strong>每日提醒</strong>
              <p>在固定时间提醒你完成当天学习任务。</p>
            </div>
            <el-switch v-model="form.dailyReminder" />
          </div>
          <div class="preference-item">
            <div>
              <strong>AI 调整建议</strong>
              <p>根据近期进度变化，自动生成学习节奏建议。</p>
            </div>
            <el-switch v-model="form.aiSuggestion" />
          </div>
          <div class="preference-item">
            <div>
              <strong>错题复习提醒</strong>
              <p>连续未复习的错题会优先提醒你回顾。</p>
            </div>
            <el-switch v-model="form.wrongReminder" />
          </div>
        </div>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>学习节奏</h2>
        </div>
        <div class="setting-block">
          <label class="field">
            <span>每周学习时长目标</span>
            <el-slider v-model="form.weeklyHours" :min="2" :max="20" />
          </label>
          <label class="field">
            <span>偏好资源类型</span>
            <el-checkbox-group v-model="form.preferences">
              <el-checkbox label="视频课程" />
              <el-checkbox label="练习题" />
              <el-checkbox label="讲义文档" />
              <el-checkbox label="项目案例" />
            </el-checkbox-group>
          </label>
        </div>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>安全设置</h2>
        </div>
        <div class="security-list">
          <div class="security-item">
            <div>
              <strong>登录密码</strong>
              <p>建议定期更新密码，提升账号安全性。</p>
            </div>
            <el-button @click="handleChangePwd">修改密码</el-button>
          </div>
          <div class="security-item">
            <div>
              <strong>设备登录提醒</strong>
              <p>新设备登录时，向你的邮箱发送通知。</p>
            </div>
            <el-switch v-model="form.deviceAlert" />
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/userStore'

const userStore = useUserStore()

const form = reactive({
  username: userStore.user?.username || '李同学',
  email: userStore.user?.email || 'student@example.com',
  grade: '初二',
  goal: '提分',
  dailyReminder: true,
  aiSuggestion: true,
  wrongReminder: true,
  deviceAlert: true,
  weeklyHours: 8,
  preferences: ['视频课程', '练习题', '讲义文档'],
})

function saveSettings() {
  if (userStore.user) {
    userStore.user.username = form.username
    userStore.user.email = form.email
    localStorage.setItem('user', JSON.stringify(userStore.user))
  }
  localStorage.setItem('settings', JSON.stringify({
    grade: form.grade, goal: form.goal, dailyReminder: form.dailyReminder,
    aiSuggestion: form.aiSuggestion, wrongReminder: form.wrongReminder,
    deviceAlert: form.deviceAlert, weeklyHours: form.weeklyHours, preferences: form.preferences,
  }))
  ElMessage.success('设置已保存')
}

function handleChangePwd() {
  ElMessage.info('密码修改功能请联系管理员或通过登录页"忘记密码"处理')
}

const saved = JSON.parse(localStorage.getItem('settings') || '{}')
if (saved.grade) form.grade = saved.grade
if (saved.goal) form.goal = saved.goal
if (saved.weeklyHours) form.weeklyHours = saved.weeklyHours
if (saved.preferences) form.preferences = saved.preferences
if (saved.dailyReminder !== undefined) form.dailyReminder = saved.dailyReminder
</script>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card,
.surface-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.hero-card {
  padding: 22px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.hero-label {
  color: #2b6cff;
  font-size: 0.78rem;
}

.hero-card h1 {
  margin-top: 8px;
  color: #1e293b;
  font-size: 1.8rem;
}

.hero-desc {
  margin-top: 8px;
  max-width: 680px;
  color: #64748b;
  font-size: 0.9rem;
  line-height: 1.7;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.surface-card {
  padding: 18px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h2 {
  color: #1e293b;
  font-size: 1rem;
}

.form-grid,
.setting-block,
.preference-list,
.security-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field span,
.preference-item p,
.security-item p {
  color: #64748b;
  font-size: 0.8rem;
}

.preference-item,
.security-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid #edf2f8;
  border-radius: 14px;
  background: #fbfcff;
}

.preference-item strong,
.security-item strong {
  color: #1e293b;
  font-size: 0.88rem;
}

.preference-item p,
.security-item p {
  margin-top: 4px;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .hero-card,
  .preference-item,
  .security-item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
