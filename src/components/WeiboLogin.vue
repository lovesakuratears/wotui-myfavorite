<script setup>
import { ref } from 'vue'

// 定义事件
const emit = defineEmits(['cookie-received', 'close'])

// 登录表单数据
const username = ref('')
const password = ref('')
const isLoading = ref(false)
const message = ref('')
const messageType = ref('') // success, error, info
const cookie = ref('')

// 登录方法
async function login() {
  if (!username.value || !password.value) {
    message.value = '请输入用户名和密码'
    messageType.value = 'error'
    return
  }

  isLoading.value = true
  message.value = '正在登录微博...'
  messageType.value = 'info'

  try {
    const response = await fetch('/weibo/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    })

    const data = await response.json()

    if (response.ok) {
      message.value = '登录成功，已获取Cookie'
      messageType.value = 'success'
      cookie.value = data.cookie
      // 保存到配置
      await saveCookieToConfig(data.cookie)
    } else {
      message.value = data.error || '登录失败'
      messageType.value = 'error'
    }
  } catch (error) {
    message.value = `登录失败: ${error.message}`
    messageType.value = 'error'
  } finally {
    isLoading.value = false
  }
}

// 保存Cookie到配置
async function saveCookieToConfig(cookieValue) {
  try {
    const response = await fetch('/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        cookie: cookieValue
      })
    })

    if (!response.ok) {
      throw new Error('保存Cookie失败')
    }
    
    // 通知父组件获取到了cookie
    emit('cookie-received', cookieValue)
  } catch (error) {
    console.error('保存Cookie失败:', error)
  }
}

// 复制Cookie到剪贴板
function copyCookie() {
  if (!cookie.value) {
    message.value = '没有可复制的Cookie'
    messageType.value = 'error'
    return
  }

  navigator.clipboard.writeText(cookie.value)
    .then(() => {
      message.value = 'Cookie已复制到剪贴板'
      messageType.value = 'success'
    })
    .catch(() => {
      message.value = '复制失败，请手动复制'
      messageType.value = 'error'
    })
}
</script>

<template>
  <section id="weibo-login" class="mb-12">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover-scale">
      <h2 class="text-2xl font-bold mb-6">微博Cookie获取</h2>
      
      <!-- 消息提示 -->
      <div v-if="message" class="mb-4 p-4 rounded-lg" :class="{
        'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300': messageType === 'success',
        'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300': messageType === 'error',
        'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300': messageType === 'info'
      }">
        {{ message }}
      </div>

      <!-- 登录表单 -->
      <div class="max-w-md">
        <form @submit.prevent="login">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">微博用户名</label>
            <input 
              type="text" 
              id="username" 
              class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" 
              placeholder="请输入微博用户名" 
              v-model="username"
              :disabled="isLoading"
            >
          </div>
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">微博密码</label>
            <input 
              type="password" 
              id="password" 
              class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" 
              placeholder="请输入微博密码" 
              v-model="password"
              :disabled="isLoading"
            >
          </div>
          <button 
            type="submit" 
            id="login-btn" 
            class="w-full px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors flex items-center justify-center"
            :disabled="isLoading"
          >
            <i v-if="isLoading" class="fa fa-spinner fa-spin mr-2"></i>
            {{ isLoading ? '登录中...' : '登录微博获取Cookie' }}
          </button>
        </form>
      </div>

      <!-- Cookie显示区域 -->
      <div v-if="cookie" class="mt-8">
        <h3 class="text-lg font-semibold mb-3">获取到的Cookie</h3>
        <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 relative">
          <textarea 
            class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none resize-none" 
            rows="4" 
            readonly
            v-model="cookie"
          ></textarea>
          <button 
            class="absolute top-4 right-4 px-3 py-1 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm"
            @click="copyCookie"
          >
            <i class="fa fa-copy mr-1"></i>复制
          </button>
        </div>
        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Cookie已自动保存到配置中，您可以在配置管理页面查看和修改。
        </p>
      </div>

      <!-- 操作说明 -->
      <div class="mt-8 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <h3 class="text-lg font-semibold mb-2">操作说明</h3>
        <ol class="list-decimal list-inside space-y-2 text-sm text-gray-600 dark:text-gray-300">
          <li>在上方输入您的微博账号和密码</li>
          <li>点击"登录微博获取Cookie"按钮</li>
          <li>系统会自动登录微博并获取Cookie</li>
          <li>获取到的Cookie会自动保存到配置中</li>
          <li>您也可以手动复制Cookie备用</li>
        </ol>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 组件特定样式 */
.hover-scale {
  transition: transform 0.2s ease;
}

.hover-scale:hover {
  transform: scale(1.02);
}
</style>