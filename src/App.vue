<script setup>
import { ref, onMounted, computed } from 'vue'
import Dashboard from './components/Dashboard.vue'
import Config from './components/Config.vue'
import Tasks from './components/Tasks.vue'
import Results from './components/Results.vue'
import About from './components/About.vue'
import PhotoWall from './components/PhotoWall.vue'
import ImageViewer from './components/ImageViewer.vue'

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
</script>

<template>
  <div class="bg-blue-50 dark:bg-gray-900 text-gray-800 dark:text-gray-100 min-h-screen flex flex-col transition-all duration-300">
    <!-- 顶部导航栏 -->
    <header class="fixed top-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 shadow-md transition-all duration-300 backdrop-blur-sm bg-opacity-95 dark:bg-opacity-95 border-b border-blue-200 dark:border-blue-900/50">
      <div class="container mx-auto px-4 flex items-center justify-between h-16">
        <div class="flex items-center space-x-3 group">
          <div class="bg-blue-100 dark:bg-blue-900/30 p-2 rounded-lg transition-all duration-300 transform hover:scale-110 hover:bg-blue-200 dark:hover:bg-blue-900/50">
            <img src="/icons/logo.svg" alt="Logo" class="h-8 w-8 text-blue-600 dark:text-blue-400">
          </div>
          <h1 class="text-xl font-bold text-blue-600 dark:text-blue-400 transition-all duration-300 group-hover:scale-105">我推 - My Favorite</h1>
        </div>
        <div class="flex items-center space-x-4">
          <div class="relative flex items-center space-x-2 group">
            <span id="status-indicator" class="inline-block w-3 h-3 bg-blue-400 dark:bg-blue-500 rounded-full transition-all duration-500 animate-pulse group-hover:scale-125"></span>
            <span id="status-text" class="text-sm font-medium text-gray-600 dark:text-gray-300 transition-colors duration-300 group-hover:text-blue-600 dark:group-hover:text-blue-400">未运行</span>
          </div>
          <button id="theme-toggle" class="p-2 rounded-full bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-all duration-300 shadow-sm hover:shadow-md transform hover:scale-110 active:scale-95">
            <i class="fa fa-moon-o text-blue-600 dark:text-yellow-400 dark:hidden transition-all duration-300 hover:rotate-180"></i>
            <i class="fa fa-sun-o text-yellow-500 dark:text-blue-300 hidden dark:block transition-all duration-300 hover:rotate-180"></i>
          </button>
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
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                :class="activeNav === 'photo-wall' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium' : ''"
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
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                :class="activeNav === 'dashboard' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium' : ''"
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
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                :class="activeNav === 'config' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium' : ''"
                @click.prevent="switchNav('config')"
              >
                <i class="fa fa-cog text-lg"></i>
                <span>配置管理</span>
              </a>
            </li>
            <!-- 任务执行导航项 -->
            <li>
              <a 
                href="#tasks" 
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                :class="activeNav === 'tasks' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium' : ''"
                @click.prevent="switchNav('tasks')"
              >
                <i class="fa fa-tasks text-lg"></i>
                <span>任务执行</span>
              </a>
            </li>
            <!-- 结果管理导航项 -->
            <li>
              <a 
                href="#results" 
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                :class="activeNav === 'results' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium' : ''"
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
                class="nav-link flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                :class="activeNav === 'about' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium' : ''"
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
        <!-- 照片墙组件 -->
        <PhotoWall v-if="activeNav === 'photo-wall'" @show-file-modal="showFileModal" @view-images="showImageViewerModal" />
        <!-- 仪表盘组件 -->
        <Dashboard v-else-if="activeNav === 'dashboard'" @show-file-modal="showFileModal" @view-images="showImageViewerModal" />
        <!-- 配置管理组件 -->
        <Config v-else-if="activeNav === 'config'" @show-file-modal="showFileModal" @view-images="showImageViewerModal" />
        <!-- 任务执行组件 -->
        <Tasks v-else-if="activeNav === 'tasks'" @show-file-modal="showFileModal" @view-images="showImageViewerModal" />
        <!-- 结果管理组件 -->
        <Results v-else-if="activeNav === 'results'" @show-file-modal="showFileModal" @view-images="showImageViewerModal" />
        <!-- 关于组件 -->
        <About v-else-if="activeNav === 'about'" @show-file-modal="showFileModal" @view-images="showImageViewerModal" />
        <!-- 默认显示仪表盘 -->
        <Dashboard v-else @show-file-modal="showFileModal" @view-images="showImageViewerModal" />
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
  </div>
</template>

<style>
/* 自定义工具类 */
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
</style>

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
</style>