<template>
  <PageContainer :title="t('users.title')" :sub-title="t('users.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">
      <el-input v-model="q" size="small" :placeholder="t('users.searchPlaceholder')" class="pro-control-lg" @keyup.enter="load" clearable />
      <el-button type="danger" size="small" @click="load">{{ t('common.search') }}</el-button>
    </WorkspaceFilter>
    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="id" :label="t('common.id')" :width="72" />
      <el-table-column :label="t('users.app')" width="110">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ appLabel(row.app_id) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="nickname" :label="t('users.nickname')">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">{{ row.nickname || '-' }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="email" :label="t('common.email')" min-width="160" />
      <el-table-column :label="t('users.loginType')" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="loginTypeTag(row.login_type)">{{ loginTypeText(row.login_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="country" :label="t('users.region')" width="100">
        <template #default="{ row }">{{ regionText(row.country) }}</template>
      </el-table-column>
      <el-table-column prop="locale" :label="t('users.lang')" width="100">
        <template #default="{ row }">{{ localeText(row.locale) }}</template>
      </el-table-column>
      <el-table-column prop="city" :label="t('users.city')" width="100" />
      <el-table-column prop="abc_grade" :label="t('users.grade')" width="90">
        <template #default="{ row }">
          <el-tag :type="gradeType(row.abc_grade)" size="small">{{ row.abc_grade || 'C' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="vip_tier" :label="t('users.vip')" width="100" />
      <el-table-column prop="has_recharged" :label="t('users.paid')" width="80">
        <template #default="{ row }">{{ row.has_recharged ? t('common.yes') : t('common.no') }}</template>
      </el-table-column>
      <el-table-column prop="status" :label="t('common.status')" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? t('common.ok') : t('common.ban') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="160" />
      <el-table-column :label="t('common.actions')" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">{{ t('users.detail') }}</el-button>
          <el-button link type="primary" @click="openGrant(row)">{{ t('users.grantVip') }}</el-button>
          <el-button link type="warning" @click="clearVip(row)">{{ t('users.clearVip') }}</el-button>
          <el-button link type="danger" @click="toggleBan(row)">
            {{ row.status === 1 ? t('common.ban') : t('common.unban') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager" v-if="total">
      <span>{{ t('common.total', { n: total }) }}</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="sizes, prev, pager, next"
        background
        small
        @current-change="load"
        @size-change="onPageSizeChange"
      />
    </div>

    <!-- User detail drawer -->
    <el-drawer v-model="detailVisible" :title="t('users.detailTitle')" size="480px" destroy-on-close>
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <div class="detail-photos" v-if="(detail.photos || []).length">
            <el-image
              v-for="p in detail.photos"
              :key="p.id || p.url"
              :src="p.url"
              fit="cover"
              class="detail-photo"
              :preview-src-list="(detail.photos || []).map((x) => x.url)"
            />
          </div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item :label="t('common.id')">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.nickname')">{{ detail.nickname }}</el-descriptions-item>
            <el-descriptions-item :label="t('common.email')">{{ detail.email }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.app')">{{ appLabel(detail.app_id) }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.loginType')">{{ loginTypeText(detail.login_type) }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.age')">{{ detail.age ?? '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.gender')">{{ detail.gender || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.city')">{{ detail.city || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.region')">{{ regionText(detail.country) }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.lang')">{{ localeText(detail.locale) }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.job')">{{ detail.job || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.bio')">{{ detail.bio || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.lookingFor')">{{ detail.looking_for || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.mbti')">{{ detail.mbti || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.zodiac')">{{ detail.zodiac || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.relationship')">{{ detail.relationship || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.interests')">
              {{ (detail.interests || []).length ? detail.interests.join(', ') : '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('users.vip')">{{ detail.vip_tier || 'none' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.vipExpire')">{{ detail.vip_expire_at || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.grade')">{{ detail.abc_grade || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('users.balances')">
              SL {{ detail.balances?.super_like ?? 0 }} /
              Boost {{ detail.balances?.boost ?? 0 }} /
              Rewind {{ detail.balances?.rewind ?? 0 }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('common.status')">
              {{ detail.status === 1 ? t('common.ok') : t('common.ban') }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('common.createdAt')">{{ detail.created_at }}</el-descriptions-item>
          </el-descriptions>
          <div class="detail-actions">
            <el-button type="primary" @click="openGrant(detail)">{{ t('users.grantVip') }}</el-button>
            <el-button type="warning" @click="clearVip(detail)">{{ t('users.clearVip') }}</el-button>
            <el-button type="danger" @click="toggleBan(detail)">
              {{ detail.status === 1 ? t('common.ban') : t('common.unban') }}
            </el-button>
          </div>
        </template>
      </div>
    </el-drawer>

    <!-- Grant privilege dialog -->
    <el-dialog v-model="grantVisible" :title="t('users.grantTitle')" :width="440" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item :label="t('users.grantType')">
          <el-radio-group v-model="grantForm.mode">
            <el-radio-button label="vip">VIP</el-radio-button>
            <el-radio-button label="entitlement">{{ t('users.consumable') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="grantForm.mode === 'vip'">
          <el-form-item :label="t('users.vipTier')">
            <el-select v-model="grantForm.tier" style="width:100%">
              <el-option label="Plus" value="plus" />
              <el-option label="Gold" value="gold" />
              <el-option label="Platinum" value="platinum" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('users.duration')">
            <div class="grant-unit-row">
              <el-input-number v-model="grantForm.amount" :min="1" :max="3650" />
              <el-select v-model="grantForm.unit" style="width:110px">
                <el-option :label="t('users.unitDay')" value="day" />
                <el-option :label="t('users.unitMonth')" value="month" />
              </el-select>
            </div>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item :label="t('users.consumableKind')">
            <el-select v-model="grantForm.kind" style="width:100%">
              <el-option label="Super Like" value="super_like" />
              <el-option label="Boost" value="boost" />
              <el-option label="Rewind" value="rewind" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('users.quantity')">
            <el-input-number v-model="grantForm.quantity" :min="1" :max="9999" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="grantVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="grantSaving" @click="submitGrant">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, getUserDetail, userAction } from '../api'
import { workspaceAppId, getAppOptions } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t, te } = useI18n()
const q = ref('')
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(50)

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

const grantVisible = ref(false)
const grantSaving = ref(false)
const grantTarget = ref(null)
const grantForm = reactive({
  mode: 'vip',
  tier: 'gold',
  amount: 1,
  unit: 'month',
  kind: 'super_like',
  quantity: 1
})

function gradeType(g) {
  if (g === 'A') return 'danger'
  if (g === 'B') return 'warning'
  return 'info'
}

function appLabel(appId) {
  const hit = getAppOptions().find((o) => o.value === appId)
  return hit ? hit.label : (appId || '-')
}

function loginTypeText(type) {
  const key = `users.loginTypes.${type || 'email'}`
  return te(key) ? t(key) : (type || 'email')
}

function loginTypeTag(type) {
  if (type === 'google') return 'success'
  if (type === 'apple') return 'warning'
  return 'info'
}

function regionText(code) {
  if (!code) return '-'
  const key = `regions.${code}`
  return te(key) ? t(key) : code
}

function localeText(code) {
  if (!code) return '-'
  const key = `locales.${code}`
  return te(key) ? t(key) : code
}

function onPageSizeChange() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const res = await getUsers({
      app_id: workspaceAppId(),
      q: q.value,
      currentPage: page.value,
      pageSize: pageSize.value
    })
    rows.value = res.results || []
    total.value = (res.pagination && res.pagination.total) || rows.value.length
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const res = await getUserDetail({ user_id: row.id })
    detail.value = res.results || res
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

function openGrant(row) {
  grantTarget.value = row
  grantForm.mode = 'vip'
  grantForm.tier = 'gold'
  grantForm.amount = 1
  grantForm.unit = 'month'
  grantForm.kind = 'super_like'
  grantForm.quantity = 1
  grantVisible.value = true
}

async function submitGrant() {
  if (!grantTarget.value) return
  grantSaving.value = true
  try {
    if (grantForm.mode === 'vip') {
      await userAction({
        user_id: grantTarget.value.id,
        action: 'grant_vip',
        tier: grantForm.tier,
        amount: grantForm.amount,
        unit: grantForm.unit
      })
      ElMessage.success(t('users.granted', { tier: grantForm.tier }))
    } else {
      await userAction({
        user_id: grantTarget.value.id,
        action: 'grant_entitlement',
        kind: grantForm.kind,
        quantity: grantForm.quantity
      })
      ElMessage.success(t('users.grantedEntitlement', { kind: grantForm.kind, n: grantForm.quantity }))
    }
    grantVisible.value = false
    await load()
    if (detailVisible.value && detail.value?.id === grantTarget.value.id) {
      await openDetail(grantTarget.value)
    }
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    grantSaving.value = false
  }
}

async function clearVip(row) {
  try {
    await ElMessageBox.confirm(t('users.clearVipConfirm'), t('users.clearVip'), { type: 'warning' })
  } catch {
    return
  }
  try {
    await userAction({ user_id: row.id, action: 'clear_vip' })
    ElMessage.success(t('users.cleared'))
    await load()
    if (detailVisible.value && detail.value?.id === row.id) {
      await openDetail(row)
    }
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function toggleBan(row) {
  try {
    await userAction({ user_id: row.id, action: row.status === 1 ? 'ban' : 'unban' })
    ElMessage.success(t('users.updated'))
    await load()
    if (detailVisible.value && detail.value?.id === row.id) {
      await openDetail(row)
    }
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

onMounted(load)
</script>

<style scoped>
.pager {
  margin-top: var(--pro-space-md);
  color: var(--pro-text-secondary);
  font-size: var(--pro-font-sm);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.detail-body { padding-bottom: 24px; }
.detail-photos {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.detail-photo {
  width: 88px;
  height: 88px;
  border-radius: 8px;
  overflow: hidden;
}
.detail-actions {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.grant-unit-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
</style>
