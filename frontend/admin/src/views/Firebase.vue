<template>
  <PageContainer :title="t('firebase.title')" :sub-title="t('firebase.subtitle')" :ghost="true">
    <WorkspaceFilter :show-country="false" @change="load" />
    <el-card shadow="never">
      <PageTabs v-model="tab" :tabs="tabs">
        <template #default="{ active }">
          <el-table v-show="active === 'users'" :data="users" style="width:100%">
            <el-table-column prop="firebase_uid" :label="t('firebase.uid')" />
            <el-table-column prop="email" :label="t('firebase.email')" />
            <el-table-column prop="username" :label="t('firebase.username')" />
          </el-table>
          <el-table v-show="active === 'orders'" :data="orders" style="width:100%">
            <el-table-column prop="order_id" :label="t('firebase.order')" />
            <el-table-column prop="product_id" :label="t('firebase.product')" />
            <el-table-column prop="status" :label="t('firebase.status')" />
          </el-table>
          <el-table v-show="active === 'payments'" :data="payments" style="width:100%">
            <el-table-column prop="transaction_id" :label="t('firebase.txn')" />
            <el-table-column prop="order_id" :label="t('firebase.order')" />
            <el-table-column prop="status" :label="t('firebase.status')" />
          </el-table>
        </template>
      </PageTabs>
    </el-card>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { getFirebaseUsers, getFirebaseOrders, getFirebasePayments } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'
import PageTabs from '../components/PageTabs.vue'

const { t } = useI18n()
const tabs = computed(() => [
  { name: 'users', label: t('firebase.tabUsers') },
  { name: 'orders', label: t('firebase.tabOrders') },
  { name: 'payments', label: t('firebase.tabPayments') }
])
const tab = ref('users')
const users = ref([])
const orders = ref([])
const payments = ref([])

async function load() {
  const [u, o, p] = await Promise.all([
    getFirebaseUsers({ app_id: workspaceAppId() }),
    getFirebaseOrders({ app_id: workspaceAppId() }),
    getFirebasePayments({ app_id: workspaceAppId() })
  ])
  users.value = (u.results && u.results.list) || []
  orders.value = (o.results && o.results.list) || []
  payments.value = (p.results && p.results.list) || []
}

onMounted(load)
</script>
