<template>
  <div class="admin-page">
    <div class="admin-header">
      <h1>管理员中心</h1>
      <p>管理平台资源、用户和知识标签</p>
    </div>

    <el-row :gutter="16" class="admin-stats">
      <el-col :span="6">
        <div class="stat-card"><span class="stat-num">16</span><span class="stat-lbl">平台资源</span></div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card"><span class="stat-num">{{ userCount }}</span><span class="stat-lbl">注册用户</span></div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card"><span class="stat-num">8</span><span class="stat-lbl">知识点标签</span></div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card"><span class="stat-num">{{ genCount }}</span><span class="stat-lbl">生成资源</span></div>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab" class="admin-tabs">
      <el-tab-pane label="资源管理" name="resources">
        <el-table :data="resources" stripe style="width:100%" @row-click="editResource">
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="resource_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ typeMap[row.resource_type] || row.resource_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="direction" label="方向" width="100" />
          <el-table-column prop="difficulty" label="难度" width="80" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click.stop="editResource(row)">编辑</el-button>
              <el-button size="small" text type="danger" @click.stop="deleteResource(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button type="primary" class="add-btn" @click="showAddDialog = true">+ 新增资源</el-button>
      </el-tab-pane>

      <el-tab-pane label="用户管理" name="users">
        <el-table :data="users" stripe style="width:100%">
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">{{ row.role }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" />
          <el-table-column prop="created_at" label="注册时间" width="180" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Dify 配置" name="dify">
        <el-form label-position="top" style="max-width:500px">
          <el-form-item label="Dify 工作流地址">
            <el-input v-model="difyConfig.profile_url" placeholder="画像生成工作流 URL" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="difyConfig.profile_key" placeholder="画像生成 API Key" type="password" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveDifyConfig">保存配置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <!-- Add Resource Dialog -->
    <el-dialog v-model="showAddDialog" title="新增资源" width="500px">
      <el-form label-position="top">
        <el-form-item label="标题"><el-input v-model="newResource.title" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="类型">
              <el-select v-model="newResource.resource_type" style="width:100%">
                <el-option label="课程" value="course" />
                <el-option label="文档" value="document" />
                <el-option label="视频" value="video" />
                <el-option label="题库" value="quiz" />
                <el-option label="项目" value="project" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="方向">
              <el-select v-model="newResource.direction" style="width:100%">
                <el-option label="AI" value="AI" />
                <el-option label="后端开发" value="后端开发" />
                <el-option label="前端开发" value="前端开发" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="难度">
              <el-select v-model="newResource.difficulty" style="width:100%">
                <el-option label="入门" value="beginner" />
                <el-option label="中级" value="intermediate" />
                <el-option label="高级" value="advanced" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="newResource.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addResource">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getResources } from '@/api/resource'
import { getMe } from '@/api/auth'

const activeTab = ref('resources')
const resources = ref([])
const users = ref([])
const userCount = ref(0)
const genCount = ref(0)
const showAddDialog = ref(false)

const typeMap = { course: '课程', document: '文档', video: '视频', quiz: '题库', project: '项目' }

const newResource = ref({
  title: '',
  resource_type: 'document',
  direction: 'AI',
  difficulty: 'intermediate',
  description: '',
})

const difyConfig = ref({
  profile_url: '',
  profile_key: '',
})

onMounted(async () => {
  try {
    const res = await getResources({ page_size: 100 })
    resources.value = res.items || []
  } catch {}
  try {
    const me = await getMe()
    users.value = me ? [{ username: me.username, role: me.role, email: me.email, created_at: me.created_at }] : []
    userCount.value = users.value.length
  } catch {}
})

function editResource(row) {
  ElMessage.info('编辑功能待实现')
}
function deleteResource(row) {
  ElMessage.info('删除功能待实现')
}
function addResource() {
  ElMessage.success('新增成功（Mock）')
  showAddDialog.value = false
}
function saveDifyConfig() {
  ElMessage.success('Dify 配置已保存')
}
</script>

<style scoped>
.admin-page { max-width: 1000px; }
.admin-header { margin-bottom: 20px; }
.admin-header h1 { font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }
.admin-header p { font-size: 0.85rem; color: var(--text-secondary); }
.admin-stats { margin-bottom: 20px; }
.stat-card {
  background: white; border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 20px; text-align: center; display: flex; flex-direction: column; gap: 4px;
}
.stat-num { font-size: 1.8rem; font-weight: 700; color: var(--brand-primary); }
.stat-lbl { font-size: 0.8rem; color: var(--text-muted); }
.admin-tabs { background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px 20px; }
.add-btn { margin-top: 16px; }
</style>
