<script setup>
import { ref } from 'vue'

// 任务状态
const isRunning = ref(false)
const progress = ref(0)
const progressText = ref('0%')
const progressStatus = ref('准备就绪')
const taskLog = ref('')
let progressInterval = null

// 开始爬取任务
function startTask() {
  isRunning.value = true
  progress.value = 0
  progressText.value = '0%'
  progressStatus.value = '正在爬取...'
  taskLog.value += '开始爬取任务...\n'
  
  // 模拟进度更新
  progressInterval = setInterval(() => {
    progress.value += Math.floor(Math.random() * 10) + 1
    if (progress.value >= 100) {
      progress.value = 100
      progressText.value = '100%'
      progressStatus.value = '爬取完成'
      taskLog.value += '爬取任务完成！\n'
      clearInterval(progressInterval)
      isRunning.value = false
    } else {
      progressText.value = `${progress.value}%`
      taskLog.value += `进度更新：${progress.value}%\n`
    }
  }, 500)
}

// 停止爬取任务
function stopTask() {
  isRunning.value = false
  progressStatus.value = '已停止'
  taskLog.value += '爬取任务已停止\n'
  if (progressInterval) {
    clearInterval(progressInterval)
  }
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
        <h3 class="text-lg font-semibold mb-4">任务日志</h3>
        <div 
          id="task-log" 
          class="w-full h-64 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700/50 p-4 overflow-y-auto text-sm font-mono"
          v-html="taskLog"
        ></div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 组件特定样式 */
</style>