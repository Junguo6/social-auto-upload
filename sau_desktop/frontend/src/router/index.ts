import { createRouter, createWebHashHistory } from 'vue-router'
import PublishCenter from '../views/PublishCenter.vue'
import AccountList from '../views/AccountList.vue'
import Dashboard from '../views/Dashboard.vue'
import Settings from '../views/Settings.vue'

const routes = [
  {
    path: '/',
    name: 'PublishCenter',
    component: PublishCenter,
    meta: { title: '矩阵发布中心' }
  },
  {
    path: '/accounts',
    name: 'AccountList',
    component: AccountList,
    meta: { title: '平台账号管理' }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { title: '数据概览大盘' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: { title: '系统运行设置' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
