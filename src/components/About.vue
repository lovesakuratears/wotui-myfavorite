<script setup>
// 关于组件，主要是静态内容展示
</script>

<template>
  <!-- 关于区域 -->
  <section id="about" class="mb-12">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover-scale">
      <h2 class="text-2xl font-bold mb-6">关于</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 class="text-lg font-semibold mb-4">我推 - My Favorite</h3>
          <p class="text-gray-600 dark:text-gray-300 mb-4">这是一个功能强大的微博爬虫可视化工具，可以帮助您轻松爬取微博用户数据。</p>
          <ul class="space-y-2 text-gray-600 dark:text-gray-300">
            <li><i class="fa fa-check text-success mr-2"></i>支持多用户同时爬取</li>
            <li><i class="fa fa-check text-success mr-2"></i>支持多种数据格式导出</li>
            <li><i class="fa fa-check text-success mr-2"></i>支持图片、视频下载</li>
            <li><i class="fa fa-check text-success mr-2"></i>支持评论、转发爬取</li>
          </ul>
        </div>
        <div>
          <h3 class="text-lg font-semibold mb-4">使用说明</h3>
          <ol class="list-decimal list-inside space-y-2 text-gray-600 dark:text-gray-300">
            <li>在配置管理中设置爬取参数</li>
            <li>点击保存配置按钮</li>
            <li>在任务执行中点击开始爬取</li>
            <li>查看爬取进度和日志</li>
            <li>在结果管理中查看和下载爬取结果</li>
          </ol>
        </div>
      </div>
      
      <div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-semibold mb-4">技术栈</h3>
        <div class="flex flex-wrap gap-4">
          <div class="bg-blue-50 dark:bg-gray-700/50 px-4 py-2 rounded-full">
            <span class="text-blue-600 dark:text-blue-400 font-medium">Vue 3</span>
          </div>
          <div class="bg-green-50 dark:bg-gray-700/50 px-4 py-2 rounded-full">
            <span class="text-green-600 dark:text-green-400 font-medium">Vite</span>
          </div>
          <div class="bg-purple-50 dark:bg-gray-700/50 px-4 py-2 rounded-full">
            <span class="text-purple-600 dark:text-purple-400 font-medium">Tailwind CSS</span>
          </div>
          <div class="bg-yellow-50 dark:bg-gray-700/50 px-4 py-2 rounded-full">
            <span class="text-yellow-600 dark:text-yellow-400 font-medium">Chart.js</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 组件特定样式 */
</style>