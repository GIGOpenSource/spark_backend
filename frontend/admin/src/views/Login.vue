<template>
  <div class="pro-login">
    <div class="pro-login-card">
      <div class="pro-login-brand">
        <div class="pro-logo-mark">S</div>
        <h1>{{ t('login.title') }}</h1>
        <p>{{ t('login.subtitle') }}</p>
      </div>
      <div class="lang-row">
        <el-select v-model="localeModel" size="small" class="pro-control-xs" @change="onLocaleChange">
          <el-option label="中文" value="zh-CN" />
          <el-option label="English" value="en" />
        </el-select>
      </div>
      <el-form @submit.prevent="submit" label-position="top">
        <el-form-item :label="t('login.account')">
          <el-input v-model="username" :placeholder="t('login.accountPlaceholder')" size="large" clearable />
        </el-form-item>
        <el-form-item :label="t('login.password')">
          <el-input
            v-model="password"
            type="password"
            :placeholder="t('login.passwordPlaceholder')"
            size="large"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="danger" size="large" style="width:100%" :loading="loading" @click="submit">
          {{ t('login.submit') }}
        </el-button>
      </el-form>
      <p class="pro-login-hint">{{ t('login.hint') }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { adminLogin } from '../api'
import { setLocale } from '../i18n'
import { setAccessibleApps, setWorkspace } from '../workspace'

const { t, locale } = useI18n()
const router = useRouter()
const username = ref('spark_admin')
const password = ref('SparkAdmin1')
const loading = ref(false)
const localeModel = ref(locale.value)

function onLocaleChange(val) {
  setLocale(val)
}

async function submit() {
  loading.value = true
  try {
    const res = await adminLogin({ username: username.value, password: password.value })
    const data = res.results || {}
    localStorage.setItem('admin_token', data.token)
    localStorage.setItem('admin_username', data.username || username.value)
    localStorage.setItem('admin_role', data.role || 'operator')
    localStorage.setItem('admin_permissions', JSON.stringify(Array.isArray(data.permissions) ? data.permissions : []))
    const apps = data.admin_app_ids || (data.apps || []).map((a) => a.app_id)
    setAccessibleApps(apps)
    if (data.app_id) setWorkspace({ app_id: data.app_id })
    router.push('/')
  } catch (e) {
    ElMessage.error(e.message || t('login.failed'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.lang-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--pro-space-sm);
}
</style>
