import { createApp, watch } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import 'element-plus/dist/index.css'
import './styles/pro-layout.css'
import App from './App.vue'
import router from './router'
import i18n from './i18n'

const app = createApp(App)
app.use(router)
app.use(i18n)

const epLocale = i18n.global.locale.value === 'en' ? en : zhCn
app.use(ElementPlus, { locale: epLocale })

watch(
  () => i18n.global.locale.value,
  () => {
    // Element Plus locale is bound at install; soft reload keeps menus/i18n in sync
    document.documentElement.lang = i18n.global.locale.value === 'en' ? 'en' : 'zh-CN'
  },
  { immediate: true }
)

app.mount('#app')
