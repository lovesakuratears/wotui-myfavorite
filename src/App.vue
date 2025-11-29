<script setup>
import { ref, onMounted, computed } from 'vue'
import Dashboard from './components/Dashboard.vue'
import Config from './components/Config.vue'
import Tasks from './components/Tasks.vue'
import Results from './components/Results.vue'
import About from './components/About.vue'
import PhotoWall from './components/PhotoWall.vue'
import ImageViewer from './components/ImageViewer.vue'
import WeiboLogin from './components/WeiboLogin.vue'

// 当前激活的导航项
const activeNav = ref('dashboard')

// 主题状态
const isDarkMode = ref(false)

// 模态框状态
const showModal = ref(false)
const modalTitle = ref('')
const modalContent = ref('')

// 图片查看器状态
const showImageViewer = ref(false)
const currentUser = ref(null)

// 微博登录弹窗状态
const showWeiboLogin = ref(false)
const cookieFromLogin = ref('')

// 显示微博登录弹窗
const showWeiboLoginModal = () => {
  showWeiboLogin.value = true
}

// 关闭微博登录弹窗
const closeWeiboLoginModal = () => {
  showWeiboLogin.value = false
}

// 处理获取到的cookie
const handleCookieReceived = (cookie) => {
  cookieFromLogin.value = cookie
  closeWeiboLoginModal()
  // 可以在这里添加其他处理逻辑，比如刷新配置
}

// 计算当前显示的组件
const currentComponent = computed(() => {
  switch (activeNav.value) {
    case 'dashboard':
      return Dashboard
    case 'photo-wall':
      return PhotoWall
    case 'config':
      return Config
    case 'tasks':
      return Tasks
    case 'results':
      return Results
    case 'about':
      return About
    default:
      return Dashboard
  }
})

// 初始化主题
onMounted(() => {
  if (localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDarkMode.value = true
    document.documentElement.classList.add('dark')
  }
})

// 切换主题
const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('theme', 'light')
  }
}

// 切换导航项
const switchNav = (navItem) => {
  activeNav.value = navItem
}

// 显示文件预览模态框
const showFileModal = (user) => {
  modalTitle.value = `${user} 的文件列表`
  // 模拟文件列表
  modalContent.value = `
    <div class="space-y-4">
      <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="flex items-center">
          <i class="fa fa-file-text text-blue-500 text-xl mr-3"></i>
          <div>
            <p class="font-medium">${user}_data.csv</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">2.5 MB · CSV文件</p>
          </div>
        </div>
        <div class="flex space-x-2">
          <button class="px-3 py-1 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm">预览</button>
          <button class="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-sm">下载</button>
        </div>
      </div>
      <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="flex items-center">
          <i class="fa fa-file-text text-red-500 text-xl mr-3"></i>
          <div>
            <p class="font-medium">${user}_data.json</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">3.8 MB · JSON文件</p>
          </div>
        </div>
        <div class="flex space-x-2">
          <button class="px-3 py-1 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm">预览</button>
          <button class="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-sm">下载</button>
        </div>
      </div>
      <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="flex items-center">
          <i class="fa fa-folder text-yellow-500 text-xl mr-3"></i>
          <div>
            <p class="font-medium">images/</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">36 个文件</p>
          </div>
        </div>
        <div class="flex space-x-2">
          <button class="px-3 py-1 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm">查看</button>
          <button class="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-sm">下载</button>
        </div>
      </div>
      <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="flex items-center">
          <i class="fa fa-folder text-green-500 text-xl mr-3"></i>
          <div>
            <p class="font-medium">videos/</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">12 个文件</p>
          </div>
        </div>
        <div class="flex space-x-2">
          <button class="px-3 py-1 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm">查看</button>
          <button class="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-sm">下载</button>
        </div>
      </div>
    </div>
  `
  showModal.value = true
}

// 显示图片查看器
const showImageViewerModal = (user) => {
  currentUser.value = user
  showImageViewer.value = true
}

// 关闭模态框
const closeModal = () => {
  showModal.value = false
}

// 关闭图片查看器
const closeImageViewer = () => {
  showImageViewer.value = false
  currentUser.value = null
}

// 显示微博登录弹窗
const showWeiboLoginModal = () => {
  showWeiboLogin.value = true
}

// 关闭微博登录弹窗
const closeWeiboLoginModal = () => {
  showWeiboLogin.value = false
}

// 处理获取到的cookie
const handleCookieReceived = (cookie) => {
  cookieFromLogin.value = cookie
  closeWeiboLoginModal()
  // 可以在这里添加其他处理逻辑，比如刷新配置
}
</script>

<template>
  <div class="bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-100 min-h-screen flex flex-col transition-all duration-300">
    <!-- 顶部导航栏 -->
    <header class="fixed top-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 shadow-sm transition-all duration-300">
      <div class="container mx-auto px-4 flex items-center justify-between h-16">
        <div class="flex items-center space-x-2">
          <img src="/static/icons/logo.svg" alt="Logo" class="h-8 w-8">
          <h1 class="text-xl font-bold text-primary dark:text-secondary">我推 - My Favorite</h1>
        </div>
        <div class="flex items-center space-x-4">
          <button id="theme-toggle" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors" @click="toggleTheme">
            <i class="fa fa-moon-o dark:hidden"></i>
            <i class="fa fa-sun-o hidden dark:block"></i>
          </button>
          <div class="relative">
            <span id="status-indicator" class="inline-block w-3 h-3 bg-gray-300 dark:bg-gray-600 rounded-full"></span>
            <span id="status-text" class="ml-2 text-sm">未运行</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 主要内容 -->
    <div class="flex pt-16 min-h-screen">
      <!-- 左侧导航栏 -->
      <aside id="sidebar" class="fixed left-0 top-16 bottom-0 w-64 bg-white dark:bg-gray-800 sidebar-shadow overflow-y-auto scrollbar-hide transition-all duration-300 transform z-40">
        <nav class="py-6 px-4">
          <ul class="space-y-1">
            <!-- 照片墙导航项 -->
            <li>
              <a 
                href="#photo-wall" 
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
                @click.prevent="switchNav('photo-wall')"
              >
                <i class="fa fa-th-large text-lg"></i>
                <span>照片墙</span>
              </a>
            </li>
            <!-- 仪表盘导航项 -->
            <li>
              <a 
                href="#dashboard" 
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
                @click.prevent="switchNav('dashboard')"
              >
                <i class="fa fa-dashboard text-lg"></i>
                <span>仪表盘</span>
              </a>
            </li>
            <!-- 配置管理导航项 -->
            <li>
              <a 
                href="#config" 
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
                @click.prevent="switchNav('config')"
              >
                <i class="fa fa-cog text-lg"></i>
                <span>配置管理</span>
              </a>
            </li>
            <!-- 结果管理导航项 -->
            <li>
              <a 
                href="#results" 
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
                @click.prevent="switchNav('results')"
              >
                <i class="fa fa-folder-open text-lg"></i>
                <span>结果管理</span>
              </a>
            </li>
            <!-- 关于导航项 -->
            <li>
              <a 
                href="#about" 
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
                @click.prevent="switchNav('about')"
              >
                <i class="fa fa-info-circle text-lg"></i>
                <span>关于</span>
              </a>
            </li>
          </ul>
        </nav>
      </aside>

      <!-- 右侧内容区 -->
      <main class="flex-1 ml-64 transition-all duration-300 p-6">
        <component :is="currentComponent" @show-file-modal="showFileModal" @view-images="showImageViewerModal" @get-cookie="showWeiboLoginModal" />
      </main>
    </div>

    <!-- 文件预览模态框 -->
    <div id="file-modal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" v-if="showModal">
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h3 class="text-lg font-semibold">{{ modalTitle }}</h3>
          <button id="close-modal" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors" @click="closeModal">
            <i class="fa fa-times"></i>
          </button>
        </div>
        <div class="p-4 overflow-y-auto max-h-[calc(90vh-100px)]" id="modal-content" v-html="modalContent"></div>
      </div>
    </div>

    <!-- 图片查看器模态框 -->
    <image-viewer 
      v-if="showImageViewer && currentUser" 
      :user="currentUser" 
      @close="closeImageViewer" 
    />

    <!-- 微博登录模态框 -->
    <div id="weibo-login-modal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" v-if="showWeiboLogin">
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg w-full max-w-md max-h-[90vh] overflow-hidden">
        <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h3 class="text-lg font-semibold">微博Cookie获取</h3>
          <button id="close-weibo-login" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors" @click="closeWeiboLoginModal">
            <i class="fa fa-times"></i>
          </button>
        </div>
        <div class="p-4 overflow-y-auto max-h-[calc(90vh-100px)]">
          <weibo-login @cookie-received="handleCookieReceived" @close="closeWeiboLoginModal" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 简单的图标替代样式 */
.icon {
  display: inline-block;
  width: 20px;
  height: 20px;
  background-color: #3B82F6;
  border-radius: 4px;
  position: relative;
}
.icon:before, .icon:after {
  content: '';
  position: absolute;
  background-color: white;
}
/* 简单的复选框替代 */
.checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid #3B82F6;
  border-radius: 4px;
  display: inline-block;
  position: relative;
  cursor: pointer;
}
.checkbox.checked:after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #3B82F6;
  font-weight: bold;
}

/* Tailwind 工具类 */
@layer utilities {
  .content-auto {
    content-visibility: auto;
  }
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
  .sidebar-shadow {
    box-shadow: 0 0 15px rgba(0, 0, 0, 0.07);
  }
  .transition-all-300 {
    transition: all 0.3s ease;
  }
  .hover-scale {
    transition: transform 0.2s ease;
  }
  .hover-scale:hover {
    transform: scale(1.02);
  }
}
</style>