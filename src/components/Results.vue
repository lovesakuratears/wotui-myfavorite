<script setup>
import { ref, onMounted } from 'vue'

// 定义事件
const emit = defineEmits(['show-file-modal', 'view-images'])

// 搜索和结果数据
const searchQuery = ref('')
const results = ref([])

// 页面加载时初始化数据
onMounted(() => {
  loadWeiboData()
})

// 加载weibo文件夹数据
async function loadWeiboData() {
  try {
    // 从后端API获取数据
    const response = await fetch('http://localhost:5000/results')
    const data = await response.json()
    
    // 过滤掉空对象
    results.value = data.map(user => ({
      ...user,
      files: user.files.filter(file => Object.keys(file).length > 0)
    }))
  } catch (error) {
    console.error('获取weibo数据失败:', error)
    // 如果API调用失败，使用模拟数据
    loadMockWeiboData()
  }
}

// 加载模拟数据作为备份
function loadMockWeiboData() {
  // 模拟weibo文件夹下的用户数据
  results.value = [
    {
      id: '123456',
      name: '迪丽热巴',
      weiboCount: 1245,
      fileCount: 36,
      imageCount: 28,
      lastUpdate: '2023-08-21 15:30',
      files: [
        { name: '123456_data.csv', type: 'csv', size: '2.5 MB' },
        { name: '123456_data.db', type: 'db', size: '1.8 MB' }
      ]
    },
    {
      id: '789012',
      name: '郭碧婷',
      weiboCount: 876,
      fileCount: 24,
      imageCount: 16,
      lastUpdate: '2023-08-21 14:15',
      files: [
        { name: '789012_data.csv', type: 'csv', size: '1.2 MB' },
        { name: '789012_data.db', type: 'db', size: '950 KB' }
      ]
    },
    {
      id: '345678',
      name: '杨幂',
      weiboCount: 2345,
      fileCount: 56,
      imageCount: 42,
      lastUpdate: '2023-08-21 12:45',
      files: [
        { name: '345678_data.csv', type: 'csv', size: '3.8 MB' },
        { name: '345678_data.db', type: 'db', size: '2.9 MB' }
      ]
    }
  ]
}

// 搜索结果
function searchResults() {
  // 这里可以实现实际的搜索逻辑
  console.log('搜索:', searchQuery.value)
  // 目前只是模拟搜索，实际项目中应该调用API获取搜索结果
}

// 刷新结果
function refreshResults() {
  loadWeiboData()
  console.log('刷新结果')
}

// 查看文件列表
function viewFiles(user) {
  emit('show-file-modal', user)
}

// 查看用户图片
function viewImages(user) {
  emit('view-images', user)
}

// 下载文件
function downloadFiles() {
  console.log('下载文件')
  // 这里可以实现实际的下载逻辑
  alert('下载功能开发中...')
}
</script>

<template>
  <!-- 结果管理区域 -->
  <section id="results" class="mb-12">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover-scale">
      <h2 class="text-2xl font-bold mb-6">结果管理</h2>
      <div class="flex justify-between items-center mb-4">
        <div class="relative">
          <input 
            type="text" 
            id="search-results" 
            class="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" 
            placeholder="搜索结果..."
            v-model="searchQuery"
            @input="searchResults"
          >
          <i class="fa fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
        </div>
        <button 
          id="refresh-results" 
          class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          @click="refreshResults"
        >
          <i class="fa fa-refresh mr-2"></i>刷新
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-gray-200 dark:border-gray-700">
              <th class="text-left py-3 px-4 font-semibold">用户ID</th>
              <th class="text-left py-3 px-4 font-semibold">用户名</th>
              <th class="text-left py-3 px-4 font-semibold">微博数</th>
              <th class="text-left py-3 px-4 font-semibold">图片数</th>
              <th class="text-left py-3 px-4 font-semibold">文件数</th>
              <th class="text-left py-3 px-4 font-semibold">最后更新</th>
              <th class="text-left py-3 px-4 font-semibold">操作</th>
            </tr>
          </thead>
          <tbody id="results-table">
            <tr v-if="results.length === 0">
              <td colspan="7" class="text-center py-8 text-gray-500 dark:text-gray-400">暂无数据</td>
            </tr>
            <tr 
              v-for="result in results" 
              :key="result.id" 
              class="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/30"
            >
              <td class="py-3 px-4 font-mono text-sm">{{ result.id }}</td>
              <td class="py-3 px-4"><div class="flex items-center"><div class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center mr-3"><i class="fa fa-user text-blue-500"></i></div> {{ result.name }}</div></td>
              <td class="py-3 px-4">{{ result.weiboCount }}</td>
              <td class="py-3 px-4">{{ result.imageCount }}</td>
              <td class="py-3 px-4">{{ result.fileCount }}</td>
              <td class="py-3 px-4">{{ result.lastUpdate }}</td>
              <td class="py-3 px-4">
                <button 
                  class="view-btn px-3 py-1 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm mr-2 mb-1 md:mb-0"
                  @click="viewFiles(result.name)"
                >
                  <i class="fa fa-folder-open mr-1"></i>文件
                </button>
                <button 
                  class="view-btn px-3 py-1 bg-success text-white rounded-lg hover:bg-success/90 transition-colors text-sm mr-2 mb-1 md:mb-0"
                  @click="viewImages(result)"
                >
                  <i class="fa fa-picture-o mr-1"></i>图片
                </button>
                <button 
                  class="download-btn px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-sm"
                  @click="downloadFiles"
                >
                  <i class="fa fa-download mr-1"></i>下载
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 组件特定样式 */
</style>