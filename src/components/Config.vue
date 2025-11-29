<script setup>
import { ref, onMounted } from 'vue'

// 基本配置
const userIdList = ref('')
const queryList = ref('')
const onlyCrawlOriginal = ref(0)
const sinceDateDays = ref('')
const writeCsv = ref(true)
const writeJson = ref(false)
const databaseType = ref('sqlite')

// 下载选项
const originalPic = ref(true)
const retweetPic = ref(false)
const originalVideo = ref(true)
const retweetVideo = ref(false)
const originalLivePhoto = ref(true)
const retweetLivePhoto = ref(false)
const downloadComment = ref(true)
const downloadRepost = ref(true)

// 高级配置
const cookie = ref('')
const removeHtmlTag = ref(true)
const userIdAsFolder = ref(false)

// MySQL配置
const enableMysql = ref(false)
const mysqlHost = ref('localhost')
const mysqlPort = ref('3306')
const mysqlUser = ref('root')
const mysqlPassword = ref('')
const mysqlCharset = ref('utf8mb4')

// MongoDB配置
const enableMongodb = ref(false)
const mongodbUri = ref('')

// 定期自动爬取设置
const scheduleFrequency = ref('daily')
const customInterval = ref('60')
const enableSchedule = ref(false)

// 页面加载时初始化数据
onMounted(() => {
  fetchConfig()
})

// 从后端获取配置
async function fetchConfig() {
  try {
    const response = await fetch('/config')
    const configData = await response.json()
    
    // 基本配置
    userIdList.value = Array.isArray(configData.user_id_list) ? configData.user_id_list.join(', ') : configData.user_id_list || ''
    queryList.value = configData.query_list || ''
    onlyCrawlOriginal.value = configData.only_crawl_original || 0
    sinceDateDays.value = configData.since_date || '1'
    
    // 处理写入模式
    const writeMode = configData.write_mode || []
    writeCsv.value = writeMode.includes('csv')
    writeJson.value = writeMode.includes('json')
    
    // 下载选项
    originalPic.value = configData.original_pic_download === 1
    retweetPic.value = configData.retweet_pic_download === 1
    originalVideo.value = configData.original_video_download === 1
    retweetVideo.value = configData.retweet_video_download === 1
    originalLivePhoto.value = configData.original_live_photo_download === 1
    retweetLivePhoto.value = configData.retweet_live_photo_download === 1
    downloadComment.value = configData.download_comment === 1
    downloadRepost.value = configData.download_repost === 1
    
    // 高级配置
    cookie.value = configData.cookie || ''
    removeHtmlTag.value = configData.remove_html_tag === 1
    userIdAsFolder.value = configData.user_id_as_folder_name === 1
    
    // 定期自动爬取设置
    const scheduleConfig = configData.schedule_config || {}
    enableSchedule.value = scheduleConfig.enabled === true
    scheduleFrequency.value = scheduleConfig.interval || 'daily'
    customInterval.value = scheduleConfig.custom_interval || '60'
    
    console.log('配置加载成功:', configData)
  } catch (error) {
    console.error('加载配置失败:', error)
    loadMockData() // 加载失败时使用模拟数据
  }
}

// 加载模拟数据
function loadMockData() {
  // 加载配置数据
  userIdList.value = '1669879400, 1729370543, 1266321885'
  sinceDateDays.value = '7'
  
  // 加载数据库配置
  mysqlHost.value = 'localhost'
  mysqlPort.value = '3306'
  mysqlUser.value = 'root'
  mysqlPassword.value = '123456'
  mysqlCharset.value = 'utf8mb4'
  mongodbUri.value = 'mongodb://[username:password@]host[:port][/[defaultauthdb][?options]]'
}

// 保存配置
async function saveConfig() {
  try {
    // 收集配置数据并转换为后端期望的格式
    const writeMode = []
    if (writeCsv.value) writeMode.push('csv')
    if (writeJson.value) writeMode.push('json')
    
    const config = {
      user_id_list: userIdList.value,
      query_list: queryList.value,
      only_crawl_original: onlyCrawlOriginal.value,
      since_date: sinceDateDays.value,
      write_mode: writeMode,
      original_pic_download: originalPic.value ? 1 : 0,
      retweet_pic_download: retweetPic.value ? 1 : 0,
      original_video_download: originalVideo.value ? 1 : 0,
      retweet_video_download: retweetVideo.value ? 1 : 0,
      original_live_photo_download: originalLivePhoto.value ? 1 : 0,
      retweet_live_photo_download: retweetLivePhoto.value ? 1 : 0,
      download_comment: downloadComment.value ? 1 : 0,
      comment_max_download_count: 100, // 默认值
      download_repost: downloadRepost.value ? 1 : 0,
      repost_max_download_count: 100, // 默认值
      user_id_as_folder_name: userIdAsFolder.value ? 1 : 0,
      remove_html_tag: removeHtmlTag.value ? 1 : 0,
      cookie: cookie.value,
      schedule_config: {
        enabled: enableSchedule.value,
        interval: scheduleFrequency.value,
        custom_interval: parseInt(customInterval.value) || 60
      }
    }
    
    console.log('保存配置:', config)
    
    // 发送配置到后端
    const response = await fetch('/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(config)
    })
    
    if (response.ok) {
      alert('配置已保存')
      // 重新加载配置以确保显示最新数据
      fetchConfig()
    } else {
      const errorData = await response.json()
      throw new Error(errorData.error || '保存配置失败')
    }
  } catch (error) {
    console.error('保存配置失败:', error)
    alert(`保存配置失败: ${error.message}`)
  }
}

// 数据库类型变化处理
function handleDatabaseChange() {
  if (databaseType.value === 'mysql') {
    enableMysql.value = true
    enableMongodb.value = false
  } else if (databaseType.value === 'mongodb') {
    enableMysql.value = false
    enableMongodb.value = true
  } else {
    enableMysql.value = false
    enableMongodb.value = false
  }
}
</script>

<template>
  <!-- 配置管理区域 -->
  <section id="config" class="mb-12">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover-scale">
      <h2 class="text-2xl font-bold mb-6">配置管理</h2>
      <div class="mb-8">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">基本配置</h3>
          <button id="save-config" class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors" @click="saveConfig">
            <i class="fa fa-save mr-2"></i>保存配置
          </button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">用户ID列表</label>
            <textarea id="user-id-list" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" rows="3" placeholder="请输入用户ID，多个ID用逗号分隔或换行" v-model="userIdList"></textarea>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">也可以输入user_id_list.txt文件路径</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">搜索关键词列表</label>
            <textarea id="query-list" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" rows="3" placeholder="请输入搜索关键词，多个关键词用逗号分隔或换行" v-model="queryList"></textarea>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">设置后将按关键词搜索微博</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">爬取模式</label>
            <select id="only-crawl-original" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" v-model="onlyCrawlOriginal">
              <option value="0">爬取全部微博</option>
              <option value="1">仅爬取原创微博</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">起始日期</label>
            <div class="flex space-x-2">
              <input type="number" id="since-date-days" class="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="天数" v-model="sinceDateDays">
              <span class="flex items-center text-gray-500">天前</span>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">文件存储（可多选）</label>
            <div class="grid grid-cols-2 gap-2 mb-4">
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="write-csv" class="rounded text-primary focus:ring-primary/50" v-model="writeCsv">
                <span>CSV</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="write-json" class="rounded text-primary focus:ring-primary/50" v-model="writeJson">
                <span>JSON</span>
              </label>
            </div>
            
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">数据库存储（单选）</label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label class="flex items-center space-x-2">
                <input type="radio" name="database" id="db-sqlite" class="rounded-full text-primary focus:ring-primary/50" v-model="databaseType" value="sqlite" @change="handleDatabaseChange">
                <span>SQLite</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="radio" name="database" id="db-mysql" class="rounded-full text-primary focus:ring-primary/50" v-model="databaseType" value="mysql" @change="handleDatabaseChange">
                <span>MySQL</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="radio" name="database" id="db-mongodb" class="rounded-full text-primary focus:ring-primary/50" v-model="databaseType" value="mongodb" @change="handleDatabaseChange">
                <span>MongoDB</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div class="mb-8">
        <h3 class="text-lg font-semibold mb-4">下载选项</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">图片下载</label>
            <div class="space-y-2">
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="original-pic" class="rounded text-primary focus:ring-primary/50" v-model="originalPic">
                <span>原创微博图片</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="retweet-pic" class="rounded text-primary focus:ring-primary/50" v-model="retweetPic">
                <span>转发微博图片</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="original-live-photo" class="rounded text-primary focus:ring-primary/50" v-model="originalLivePhoto">
                <span>原创微博实况照片</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="retweet-live-photo" class="rounded text-primary focus:ring-primary/50" v-model="retweetLivePhoto">
                <span>转发微博实况照片</span>
              </label>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">视频下载</label>
            <div class="space-y-2">
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="original-video" class="rounded text-primary focus:ring-primary/50" v-model="originalVideo">
                <span>原创微博视频</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="retweet-video" class="rounded text-primary focus:ring-primary/50" v-model="retweetVideo">
                <span>转发微博视频</span>
              </label>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">评论与转发</label>
            <div class="space-y-2">
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="download-comment" class="rounded text-primary focus:ring-primary/50" v-model="downloadComment">
                <span>下载评论</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="download-repost" class="rounded text-primary focus:ring-primary/50" v-model="downloadRepost">
                <span>下载转发</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div class="mb-8">
        <h3 class="text-lg font-semibold mb-4">高级配置</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Cookie</label>
            <div class="relative">
              <textarea id="cookie" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" rows="2" placeholder="your cookie" v-model="cookie"></textarea>
              <button 
                id="get-cookie-btn" 
                class="absolute top-2 right-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium shadow-sm"
                @click="$emit('get-cookie')"
              >
                <i class="fa fa-magic mr-1"></i>获取Cookie
              </button>
            </div>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">点击按钮自动获取微博Cookie，无需手动复制</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">其他选项</label>
            <div class="space-y-2">
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="remove-html-tag" class="rounded text-primary focus:ring-primary/50" v-model="removeHtmlTag">
                <span>移除HTML标签</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="checkbox" id="user-id-as-folder" class="rounded text-primary focus:ring-primary/50" v-model="userIdAsFolder">
                <span>使用用户ID作为文件夹名</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div class="mb-8" v-if="enableMysql">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">MySQL配置 <span class="text-xs text-gray-500 dark:text-gray-400">(可选)</span></h3>
          <label class="flex items-center space-x-2">
            <input type="checkbox" id="enable-mysql" class="rounded text-primary focus:ring-primary/50" v-model="enableMysql">
            <span>启用MySQL</span>
          </label>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">主机</label>
            <input type="text" id="mysql-host" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="localhost" v-model="mysqlHost">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">端口</label>
            <input type="number" id="mysql-port" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="3306" v-model="mysqlPort">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">用户名</label>
            <input type="text" id="mysql-user" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="root" v-model="mysqlUser">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">密码</label>
            <input type="password" id="mysql-password" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="password" v-model="mysqlPassword">
          </div>
          <div class="md:col-span-2 lg:col-span-4">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">字符集</label>
            <input type="text" id="mysql-charset" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="utf8mb4" v-model="mysqlCharset">
          </div>
        </div>
      </div>

      <div class="mb-8" v-if="enableMongodb">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">MongoDB配置 <span class="text-xs text-gray-500 dark:text-gray-400">(可选)</span></h3>
          <label class="flex items-center space-x-2">
            <input type="checkbox" id="enable-mongodb" class="rounded text-primary focus:ring-primary/50" v-model="enableMongodb">
            <span>启用MongoDB</span>
          </label>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">MongoDB URI</label>
          <input type="text" id="mongodb-uri" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="mongodb://[username:password@]host[:port][/[defaultauthdb][?options]]" v-model="mongodbUri">
        </div>
      </div>

      <div class="mb-8">
        <h3 class="text-lg font-semibold mb-4">定期自动爬取设置 <span class="text-xs text-gray-500 dark:text-gray-400">(可选)</span></h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">自动爬取频率</label>
            <div class="space-y-2">
              <label class="flex items-center space-x-2">
                <input type="radio" name="schedule-frequency" value="hourly" class="text-primary focus:ring-primary/50" v-model="scheduleFrequency">
                <span>每小时</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="radio" name="schedule-frequency" value="daily" class="text-primary focus:ring-primary/50" v-model="scheduleFrequency">
                <span>每天</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="radio" name="schedule-frequency" value="weekly" class="text-primary focus:ring-primary/50" v-model="scheduleFrequency">
                <span>每周</span>
              </label>
              <label class="flex items-center space-x-2">
                <input type="radio" name="schedule-frequency" value="custom" class="text-primary focus:ring-primary/50" v-model="scheduleFrequency">
                <span>自定义</span>
              </label>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">自定义间隔（分钟）</label>
            <input type="number" id="custom-interval" class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none" placeholder="60" value="60" v-model="customInterval">
            <label class="flex items-center space-x-2 mt-4">
              <input type="checkbox" id="enable-schedule" class="rounded text-primary focus:ring-primary/50" v-model="enableSchedule">
              <span>启用定期自动爬取</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 组件特定样式 */
</style>