import { createI18n } from 'vue-i18n'
import zh from './locales/zh-CN'
import en from './locales/en'

const saved = localStorage.getItem('admin_locale') || 'zh-CN'

export const i18n = createI18n({
  legacy: false,
  locale: saved,
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zh,
    en
  }
})

export function setLocale(locale) {
  i18n.global.locale.value = locale
  localStorage.setItem('admin_locale', locale)
  return locale
}

export default i18n
