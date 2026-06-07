import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'  // 中文
import router from './router'
import App from './App.vue'

const app = createApp(App)
app.use(ElementPlus, { locale: zhCn }) // 中文
app.use(router)
app.mount('#app')
