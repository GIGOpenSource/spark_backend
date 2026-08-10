<template>
  <PageContainer :title="t('orders.title')" :sub-title="t('orders.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load" />
    <PageTabs v-model="tab" :tabs="tabs">
      <template #default="{ active }">
        <div v-show="active === 'orders'">
          <el-table :data="orders" style="width:100%">
            <el-table-column prop="id" :label="t('common.id')" :width="72" />
            <el-table-column :label="t('orders.app')" width="120">
              <template #default="{ row }">{{ appLabel(row.app_id) }}</template>
            </el-table-column>
            <el-table-column prop="user_id" :label="t('orders.user')" />
            <el-table-column prop="product_id" :label="t('orders.product')" />
            <el-table-column prop="amount" :label="t('orders.amount')" />
            <el-table-column prop="status" :label="t('orders.status')" />
            <el-table-column prop="created_at" :label="t('orders.created')" />
          </el-table>
        </div>
        <div v-show="active === 'skus'">
          <div class="pro-toolbar is-end">
            <el-button type="danger" @click="openCreate">{{ t('orders.addSku') }}</el-button>
          </div>
          <el-table :data="skus" style="width:100%">
            <el-table-column :label="t('orders.app')" width="120">
              <template #default="{ row }">{{ appLabel(row.app_id) }}</template>
            </el-table-column>
            <el-table-column prop="product_id" :label="t('orders.product')" />
            <el-table-column prop="title" :label="t('orders.skuTitle')" />
            <el-table-column prop="sku_type" :label="t('orders.type')" width="120" />
            <el-table-column prop="tier" :label="t('orders.tier')" width="100" />
            <el-table-column prop="quantity" :label="t('orders.quantity')" width="80" />
            <el-table-column prop="duration_days" :label="t('orders.durationDays')" width="100" />
            <el-table-column prop="is_active" :label="t('common.active')" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? t('common.yes') : t('common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('common.actions')" width="160">
              <template #default="{ row }">
                <el-button link type="primary" @click="editSku(row)">{{ t('common.edit') }}</el-button>
                <el-button link type="danger" @click="toggleSku(row)">
                  {{ row.is_active ? t('common.disable') : t('common.enable') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </PageTabs>

    <el-dialog v-model="showForm" :title="editing ? t('orders.editSku') : t('orders.addSku')" :width="480">
      <el-form label-width="120px">
        <el-form-item :label="t('orders.app')" required>
          <el-select
            v-model="form.app_id"
            :disabled="editing"
            style="width:100%"
            :placeholder="t('orders.app')"
          >
            <el-option
              v-for="o in appOptions"
              :key="o.value"
              :label="o.label"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('orders.productId')">
          <el-input v-model="form.product_id" :disabled="editing" placeholder="plus_1m / super_like_3" />
        </el-form-item>
        <el-form-item :label="t('orders.skuTitle')">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item :label="t('orders.type')">
          <el-select v-model="form.sku_type" style="width:100%">
            <el-option label="subscription" value="subscription" />
            <el-option label="consumable" value="consumable" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('orders.tier')">
          <el-select v-model="form.tier" clearable style="width:100%">
            <el-option label="plus" value="plus" />
            <el-option label="gold" value="gold" />
            <el-option label="platinum" value="platinum" />
            <el-option label="super_like" value="super_like" />
            <el-option label="boost" value="boost" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('orders.quantity')">
          <el-input-number v-model="form.quantity" :min="1" />
        </el-form-item>
        <el-form-item :label="t('orders.durationDays')">
          <el-input-number v-model="form.duration_days" :min="0" />
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
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getOrders, getSkus, saveSku } from '../api'
import {
  workspaceAppId, accessibleAppOptions, getAppOptions
} from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'
import PageTabs from '../components/PageTabs.vue'

const { t } = useI18n()
const tabs = computed(() => [
  { name: 'orders', label: t('orders.tabOrders') },
  { name: 'skus', label: t('orders.tabSkus') }
])
const tab = ref('orders')
const orders = ref([])
const skus = ref([])
const showForm = ref(false)
const editing = ref(false)
const appOptions = computed(() => accessibleAppOptions({ includeAll: false }))
const form = reactive({
  app_id: 'spark_main',
  product_id: '',
  title: '',
  sku_type: 'subscription',
  tier: '',
  quantity: 1,
  duration_days: 30,
  is_active: true
})

function appLabel(appId) {
  const hit = getAppOptions().find((o) => o.value === appId)
  return hit ? hit.label : (appId || '-')
}

function defaultAppId() {
  const ws = workspaceAppId()
  if (ws && ws !== '*') return ws
  return null
}

async function load() {
  try {
    const [o, s] = await Promise.all([
      getOrders({ app_id: workspaceAppId() }),
      getSkus({ app_id: workspaceAppId() })
    ])
    orders.value = (o.results && o.results.list) || []
    skus.value = (s.results && s.results.list) || []
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

function openCreate() {
  const appId = defaultAppId()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  editing.value = false
  Object.assign(form, {
    app_id: appId,
    product_id: '',
    title: '',
    sku_type: 'subscription',
    tier: 'plus',
    quantity: 1,
    duration_days: 30,
    is_active: true
  })
  showForm.value = true
}

function editSku(row) {
  editing.value = true
  Object.assign(form, {
    app_id: row.app_id || defaultAppId(),
    product_id: row.product_id,
    title: row.title || '',
    sku_type: row.sku_type || 'subscription',
    tier: row.tier || '',
    quantity: row.quantity || 1,
    duration_days: row.duration_days || 0,
    is_active: row.is_active !== false
  })
  showForm.value = true
}

async function save() {
  if (!form.app_id || form.app_id === '*') {
    ElMessage.warning(t('orders.appRequired') || t('common.pickApp'))
    return
  }
  if (!form.product_id) {
    ElMessage.warning(t('orders.productIdRequired'))
    return
  }
  try {
    await saveSku({
      app_id: form.app_id,
      product_id: form.product_id,
      title: form.title || form.product_id,
      sku_type: form.sku_type,
      tier: form.tier || null,
      quantity: form.quantity,
      duration_days: form.duration_days || null,
      is_active: form.is_active
    })
    ElMessage.success(t('common.saved'))
    showForm.value = false
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function toggleSku(row) {
  if (!row.app_id || row.app_id === '*') {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await saveSku({
      app_id: row.app_id,
      product_id: row.product_id,
      title: row.title,
      sku_type: row.sku_type,
      tier: row.tier,
      quantity: row.quantity || 1,
      duration_days: row.duration_days,
      is_active: !row.is_active
    })
    ElMessage.success(t('common.updated'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

onMounted(load)
</script>
