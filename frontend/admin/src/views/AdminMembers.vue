<template>
  <PageContainer :title="t('admins.title')" :sub-title="t('admins.subtitle')">
    <template #extra>
      <el-button type="danger" @click="openCreate">{{ t('admins.add') }}</el-button>
      <el-button @click="load">{{ t('common.refresh') }}</el-button>
    </template>

    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="id" :label="t('common.id')" :width="72" />
      <el-table-column prop="username" :label="t('admins.account')" min-width="120" />
      <el-table-column prop="email" :label="t('admins.email')" min-width="160" />
      <el-table-column prop="role" :label="t('admins.role')" width="130">
        <template #default="{ row }">{{ roleLabel(row.role) }}</template>
      </el-table-column>
      <el-table-column :label="t('admins.apps')" min-width="160">
        <template #default="{ row }">
          {{ appLabels(row.admin_app_ids) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" :label="t('common.status')" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? t('common.enable') : t('common.disable') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="160" />
      <el-table-column :label="t('common.actions')" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button link type="danger" @click="toggleStatus(row)">
            {{ row.status === 1 ? t('common.disable') : t('common.enable') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showForm" :title="editing ? t('admins.edit') : t('admins.add')" :width="520">
      <el-form label-width="120px">
        <el-form-item :label="t('admins.account')">
          <el-input v-model="form.username" :disabled="editing" />
        </el-form-item>
        <el-form-item :label="t('admins.email')">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item v-if="!editing" :label="t('admins.password')">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item v-else :label="t('admins.newPassword')">
          <el-input v-model="form.password" type="password" show-password :placeholder="t('admins.passwordKeep')" />
        </el-form-item>
        <el-form-item :label="t('admins.role')">
          <el-select v-model="form.role" style="width:100%">
            <el-option v-for="r in roleOptions" :key="r.key" :label="roleLabel(r.key)" :value="r.key" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('admins.apps')">
          <el-select v-model="form.admin_app_ids" multiple clearable style="width:100%" :placeholder="t('admins.appsAllHint')">
            <el-option
              v-for="o in appOptions"
              :key="o.value"
              :label="o.label"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="save">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getAdminMembers, saveAdminMember, toggleAdminMember, getAdminRoles } from '../api'
import { getAppOptions, workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'

const { t, te } = useI18n()
const rows = ref([])
const loading = ref(false)
const showForm = ref(false)
const editing = ref(false)
const roleOptions = ref([])
const appOptions = computed(() => getAppOptions())
const form = reactive({
  id: null,
  username: '',
  email: '',
  password: '',
  role: 'operator',
  admin_app_ids: []
})

function roleLabel(key) {
  const k = `roles.${key}`
  return te(k) ? t(k) : key
}

function appLabels(ids) {
  if (!ids || !ids.length) return t('admins.allApps')
  const map = Object.fromEntries(getAppOptions().map((o) => [o.value, o.label]))
  return ids.map((id) => map[id] || id).join(', ')
}

async function loadRoles() {
  try {
    const res = await getAdminRoles({ app_id: workspaceAppId() })
    roleOptions.value = (res.results && res.results.roles) || []
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function load() {
  loading.value = true
  try {
    const res = await getAdminMembers()
    rows.value = res.results || []
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = false
  Object.assign(form, {
    id: null,
    username: '',
    email: '',
    password: '',
    role: 'operator',
    admin_app_ids: []
  })
  showForm.value = true
}

function openEdit(row) {
  editing.value = true
  Object.assign(form, {
    id: row.id,
    username: row.username,
    email: row.email,
    password: '',
    role: row.role,
    admin_app_ids: [...(row.admin_app_ids || [])]
  })
  showForm.value = true
}

async function save() {
  if (!form.username || !form.email) {
    ElMessage.warning(t('admins.accountEmailRequired'))
    return
  }
  if (!editing.value && !form.password) {
    ElMessage.warning(t('admins.passwordRequired'))
    return
  }
  const payload = {
    username: form.username,
    email: form.email,
    role: form.role,
    admin_app_ids: form.admin_app_ids
  }
  if (form.password) payload.password = form.password
  if (editing.value) payload.id = form.id
  try {
    await saveAdminMember(payload)
    ElMessage.success(t('common.saved'))
    showForm.value = false
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function toggleStatus(row) {
  try {
    await toggleAdminMember(row.id)
    ElMessage.success(t('admins.statusUpdated'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

onMounted(async () => {
  await loadRoles()
  await load()
})
</script>
