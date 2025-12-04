<script setup>
import { ref } from 'vue'

// 任务状态
const isRunning = ref(false)
const progress = ref(0)
const progressText = ref('0%')
const progressStatus = ref('准备就绪')
const taskLog = ref('')
const processedUsers = ref(0)
const processedWeibo = ref(0)
let progressInterval = null

// 获取当前时间戳
function getCurrentTime() {
  const now = new Date()
  return now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 添加日志条目
function addLog(message, level = 'info') {
  const timestamp = getCurrentTime()
  const logEntry = `<div class="log-entry log-${level}">[${timestamp}] ${message}</div>`
  taskLog.value += logEntry
  
  // 自动滚动到底部
  setTimeout(() => {
    const logContainer = document.getElementById('task-log')
    if (logContainer) {
      logContainer.scrollTop = logContainer.scrollHeight
    }
  }, 100)
}

// 开始爬取任务
async function startTask() {
  isRunning.value = true
  progress.value = 0
  processedUsers.value = 0
  processedWeibo.value = 0
  progressText.value = '0%'
  progressStatus.value = '正在爬取...'
  taskLog.value = '' // 清空之前的日志
  
  addLog('开始爬取任务...', 'info')
  addLog('初始化爬虫配置...', 'info')
  addLog('连接到微博服务器...', 'info')
  addLog('开始处理用户列表...', 'info')
  
  try {
    // 调用后端API开始爬取任务
    const response = await fetch('/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    const taskId = data.task_id
    
    addLog(`任务已启动，任务ID: ${taskId}`, 'success')
    
    // 轮询获取任务状态和日志
    const statusInterval = setInterval(async () => {
      try {
        const statusResponse = await fetch(`/task/${taskId}`)
        if (!statusResponse.ok) {
          throw new Error(`HTTP error! status: ${statusResponse.status}`)
        }
        
        const taskData = await statusResponse.json()
        
        // 更新进度
        if (taskData.progress !== undefined) {
          progress.value = taskData.progress
          progressText.value = `${progress.value}%`
        }
        
        // 更新状态
        if (taskData.state) {
          if (taskData.state === 'COMPLETED') {
            progressStatus.value = '爬取完成'
            clearInterval(statusInterval)
            isRunning.value = false
          } else if (taskData.state === 'FAILED') {
            progressStatus.value = '爬取失败'
            clearInterval(statusInterval)
            isRunning.value = false
          } else {
            progressStatus.value = '正在爬取...'
          }
        }
        
        // 更新日志
        if (taskData.logs && Array.isArray(taskData.logs)) {
          // 只显示新的日志
          const currentLogs = taskLog.value
          taskData.logs.forEach(log => {
            const logEntry = `<div class="log-entry log-${log.level}">[${new Date(log.timestamp).toLocaleString('zh-CN')}] ${log.message}</div>`
            if (!currentLogs.includes(logEntry)) {
              taskLog.value += logEntry
            }
          })
          
          // 自动滚动到底部
          setTimeout(() => {
            const logContainer = document.getElementById('task-log')
            if (logContainer) {
              logContainer.scrollTop = logContainer.scrollHeight
            }
          }, 100)
        }
      } catch (error) {
        console.error('获取任务状态失败:', error)
      }
    }, 1000)
    
  } catch (error) {
    console.error('启动爬取任务失败:', error)
    addLog(`启动爬取任务失败: ${error.message}`, 'error')
    isRunning.value = false
    progressStatus.value = '启动失败'
  }
}

// 停止爬取任务
async function stopTask() {
  try {
    // 调用后端API停止爬取任务
    const response = await fetch('/task/cancel', {
      method: 'POST'
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    isRunning.value = false
    progressStatus.value = '已停止'
    addLog('爬取任务已停止', 'warning')
    addLog(`当前进度：${progress.value}%`, 'info')
    addLog(`已处理用户数：${processedUsers.value}`, 'info')
    addLog(`已爬取微博数：${processedWeibo.value}`, 'info')
    
    if (progressInterval) {
      clearInterval(progressInterval)
    }
  } catch (error) {
    console.error('停止爬取任务失败:', error)
    addLog(`停止爬取任务失败: ${error.message}`, 'error')
  }
}

// 清空日志
function clearLog() {
  taskLog.value = ''
  addLog('日志已清空', 'info')
}
</script>

<template>
  <!-- 任务执行区域 -->
  <section id="tasks" class="mb-12">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover-scale">
      <h2 class="text-2xl font-bold mb-6">任务执行</h2>
      <div class="mb-6">
        <div class="flex flex-col sm:flex-row gap-4">
          <button 
            id="start-task" 
            class="px-6 py-3 bg-success text-white rounded-lg hover:bg-success/90 transition-colors flex-1 flex items-center justify-center"
            :disabled="isRunning"
            @click="startTask"
          >
            <i class="fa fa-play mr-2"></i>开始爬取
          </button>
          <button 
            id="stop-task" 
            class="px-6 py-3 bg-danger text-white rounded-lg hover:bg-danger/90 transition-colors flex-1 flex items-center justify-center"
            :disabled="!isRunning"
            @click="stopTask"
          >
            <i class="fa fa-stop mr-2"></i>停止爬取
          </button>
        </div>
      </div>
      
      <div class="mb-6">
        <h3 class="text-lg font-semibold mb-4">任务进度</h3>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 mb-2">
          <div 
            id="progress-bar" 
            class="bg-primary h-4 rounded-full transition-all duration-300"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>
        <div class="flex justify-between text-sm text-gray-600 dark:text-gray-400">
          <span id="progress-text">{{ progressText }}</span>
          <span id="progress-status">{{ progressStatus }}</span>
        </div>
      </div>

      <div>
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">任务日志</h3>
          <button 
            id="clear-log" 
            class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm font-medium rounded shadow-sm hover:shadow-md"
            @click="clearLog"
          >
            <i class="fa fa-trash mr-1"></i>清空日志
          </button>
        </div>
        <div 
          id="task-log" 
          class="w-full h-80 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 p-4 overflow-y-auto text-sm font-mono shadow-inner"
          v-html="taskLog"
        ></div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 任务日志样式 */
#task-log {
  line-height: 1.6;
}

.log-entry {
  margin-bottom: 4px;
  padding: 2px 4px;
  border-radius: 3px;
}

/* 不同级别的日志样式 */
.log-info {
  color: #374151;
  background-color: #f3f4f6;
}

.log-success {
  color: #15803d;
  background-color: #dcfce7;
}

.log-warning {
  color: #92400e;
  background-color: #fef3c7;
}

.log-error {
  color: #991b1b;
  background-color: #fee2e2;
}

/* 深色模式下的日志样式 */
.dark .log-info {
  color: #d1d5db;
  background-color: #1f2937;
}

.dark .log-success {
  color: #86efac;
  background-color: #166534;
}

.dark .log-warning {
  color: #fbbf24;
  background-color: #92400e;
}

.dark .log-error {
  color: #fca5a5;
  background-color: #7f1d1d;
}
</style>