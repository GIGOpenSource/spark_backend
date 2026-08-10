// Brand + API host
// H5 可用本机回环；真机 APP 必须用电脑局域网 IP（127.0.0.1 指向手机自己）
const develop = true
const DEV_LAN_HOST = '192.168.77.21' // 当前 Mac 局域网 IP，换网后改这里

const APP_ID = 'swipe_main'
const APP_NAME = 'bee'
const APP_NAME_DISPLAY = 'bee'
const PACKAGE_NAME = 'app.bee'
const SITE_DOMAIN = 'bee.app'
const API_DOMAIN = 'api.bee.app'

let host = 'http://127.0.0.1:8000/api'
let WS_HOST = 'ws://127.0.0.1:8000'

// #ifdef APP-PLUS
host = `http://${DEV_LAN_HOST}:8000/api`
WS_HOST = `ws://${DEV_LAN_HOST}:8000`
// #endif

if (!develop) {
	host = `https://${API_DOMAIN}/api`
	WS_HOST = `wss://${API_DOMAIN}`
}

const USE_FIREBASE_MOCK = false
const USE_IAP_MOCK = false

export {
	host,
	USE_FIREBASE_MOCK,
	USE_IAP_MOCK,
	APP_ID,
	APP_NAME,
	APP_NAME_DISPLAY,
	PACKAGE_NAME,
	SITE_DOMAIN,
	API_DOMAIN,
	WS_HOST,
	DEV_LAN_HOST
}
