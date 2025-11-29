<script setup>
import { ref, onMounted } from 'vue'

// 统计数据
const userCount = ref(0)
const weiboCount = ref(0)
const fileCount = ref(0)
const successRate = ref('0%')

// 最近爬取的用户
const recentUsers = ref([])

// 页面加载时初始化数据
onMounted(() => {
  loadMockData()
})

// 加载模拟数据
function loadMockData() {
  // 仪表盘数据
  userCount.value = 42
  weiboCount.value = 1256
  fileCount.value = 58
  successRate.value = '98%'
  
  // 最近爬取用户
  recentUsers.value = [
    { name: '迪丽热巴', weiboCount: 128, status: '成功' },
    { name: '郭碧婷', weiboCount: 85, status: '成功' },
    { name: '杨幂', weiboCount: 156, status: '成功' }
  ]
  
  // 初始化爬取趋势图表（添加错误处理）
  if (typeof Chart !== 'undefined') {
    try {
      const ctx = document.getElementById('crawl-chart').getContext('2d')
      const crawlChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
          datasets: [{
            label: '爬取微博数',
            data: [120, 190, 300, 500, 270, 430, 360],
            borderColor: '#1E40AF',
            backgroundColor: 'rgba(30, 64, 175, 0.1)',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: {
                color: 'rgba(0, 0, 0, 0.05)'
              }
            },
            x: {
              grid: {
                display: false
              }
            }
          }
        }
      })
    } catch (e) {
      console.warn('图表初始化失败:', e)
    }
  } else {
    console.warn('Chart.js未加载，跳过图表初始化')
  }
}
</script>

<template>
  <!-- 仪表盘区域 -->
  <section id="dashboard" class="mb-12">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover-scale">
      <h2 class="text-2xl font-bold mb-6">仪表盘</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-blue-50 dark:bg-gray-700/50 p-5 rounded-lg">
          <div class="flex justify-between items-start">
            <div>
              <p class="text-gray-600 dark:text-gray-300 text-sm">已爬取用户</p>
              <h3 class="text-2xl font-bold mt-1" id="user-count">{{ userCount }}</h3>
            </div>
            <div class="p-3 bg-blue-100 dark:bg-blue-900/50 rounded-full">
              <i class="fa fa-users text-blue-500"></i>
            </div>
          </div>
        </div>
        <div class="bg-green-50 dark:bg-gray-700/50 p-5 rounded-lg">
          <div class="flex justify-between items-start">
            <div>
              <p class="text-gray-600 dark:text-gray-300 text-sm">已爬取微博</p>
              <h3 class="text-2xl font-bold mt-1" id="weibo-count">{{ weiboCount }}</h3>
            </div>
            <div class="p-3 bg-green-100 dark:bg-green-900/50 rounded-full">
              <i class="fa fa-comment text-green-500"></i>
            </div>
          </div>
        </div>
        <div class="bg-purple-50 dark:bg-gray-700/50 p-5 rounded-lg">
          <div class="flex justify-between items-start">
            <div>
              <p class="text-gray-600 dark:text-gray-300 text-sm">已下载文件</p>
              <h3 class="text-2xl font-bold mt-1" id="file-count">{{ fileCount }}</h3>
            </div>
            <div class="p-3 bg-purple-100 dark:bg-purple-900/50 rounded-full">
              <i class="fa fa-download text-purple-500"></i>
            </div>
          </div>
        </div>
        <div class="bg-orange-50 dark:bg-gray-700/50 p-5 rounded-lg">
          <div class="flex justify-between items-start">
            <div>
              <p class="text-gray-600 dark:text-gray-300 text-sm">任务成功率</p>
              <h3 class="text-2xl font-bold mt-1" id="success-rate">{{ successRate }}</h3>
            </div>
            <div class="p-3 bg-orange-100 dark:bg-orange-900/50 rounded-full">
              <i class="fa fa-line-chart text-orange-500"></i>
            </div>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-gray-50 dark:bg-gray-700/50 p-5 rounded-lg">
          <h3 class="text-lg font-semibold mb-4">爬取趋势</h3>
          <div class="h-64">
            <canvas id="crawl-chart"></canvas>
          </div>
        </div>
        <div class="bg-gray-50 dark:bg-gray-700/50 p-5 rounded-lg">
          <h3 class="text-lg font-semibold mb-4">最近爬取的用户</h3>
          <div class="overflow-y-auto h-64 scrollbar-hide">
            <table class="w-full">
              <thead>
                <tr class="border-b border-gray-200 dark:border-gray-700">
                  <th class="text-left py-2 text-sm font-medium">用户</th>
                  <th class="text-left py-2 text-sm font-medium">微博数</th>
                  <th class="text-left py-2 text-sm font-medium">状态</th>
                </tr>
              </thead>
              <tbody id="recent-users">
                <tr v-if="recentUsers.length === 0">
                  <td colspan="3" class="text-center py-8 text-gray-500 dark:text-gray-400">暂无数据</td>
                </tr>
                <tr v-for="(user, index) in recentUsers" :key="index" class="border-b border-gray-200 dark:border-gray-700">
                  <td class="py-3 px-4"><div class="flex items-center"><div class="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center mr-2"><i class="fa fa-user text-blue-500"></i></div> {{ user.name }}</div></td>
                  <td class="py-3 px-4">{{ user.weiboCount }}</td>
                  <td class="py-3 px-4"><span class="px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100 rounded-full text-xs">{{ user.status }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 组件特定样式 */
</style>