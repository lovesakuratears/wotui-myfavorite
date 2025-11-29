<script setup>
import { ref, onMounted, computed } from 'vue'

// 照片墙设置
const displayCount = ref(50)
const layoutMode = ref('grid') // grid, masonry, carousel
const showControls = ref(true)

// 照片墙数据
const photoWall = ref([])
const selectedImages = ref([])
const currentPage = ref(1)
const pageSize = ref(24)

// 计算属性
const totalPages = computed(() => {
  return Math.ceil(photoWall.value.length / pageSize.value)
})

const paginatedPhotos = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return photoWall.value.slice(start, end)
})

// 初始化照片墙数据
onMounted(() => {
  loadPhotoWallData()
})

// 加载照片墙数据
function loadPhotoWallData() {
  // 从localStorage获取照片墙数据
  const savedPhotoWall = localStorage.getItem('photoWall')
  if (savedPhotoWall) {
    photoWall.value = JSON.parse(savedPhotoWall)
  } else {
    // 生成一些示例数据
    const samplePhotos = []
    for (let i = 1; i <= 30; i++) {
      samplePhotos.push({
        id: `sample_${i}`,
        url: `https://picsum.photos/800/600?random=sample_${i}`,
        thumbnail: `https://picsum.photos/200/200?random=sample_${i}`,
        filename: `sample_image_${i}.jpg`,
        size: `${Math.floor(Math.random() * 5) + 1}.${Math.floor(Math.random() * 100).toString().padStart(2, '0')} MB`,
        created: new Date().toISOString()
      })
    }
    photoWall.value = samplePhotos
    localStorage.setItem('photoWall', JSON.stringify(samplePhotos))
  }
}

// 切换图片选择状态
function toggleImageSelection(imageId) {
  const index = selectedImages.value.indexOf(imageId)
  if (index > -1) {
    selectedImages.value.splice(index, 1)
  } else {
    selectedImages.value.push(imageId)
  }
}

// 全选/取消全选
function toggleSelectAll() {
  if (selectedImages.value.length === paginatedPhotos.value.length) {
    selectedImages.value = []
  } else {
    selectedImages.value = paginatedPhotos.value.map(img => img.id)
  }
}

// 批量删除
function batchDelete() {
  if (selectedImages.value.length === 0) {
    alert('请先选择要删除的图片')
    return
  }
  
  if (confirm(`确定要删除选中的 ${selectedImages.value.length} 张图片吗？`)) {
    // 从照片墙中删除选中的图片
    photoWall.value = photoWall.value.filter(img => !selectedImages.value.includes(img.id))
    // 更新localStorage
    localStorage.setItem('photoWall', JSON.stringify(photoWall.value))
    // 清空选择
    selectedImages.value = []
    // 重置当前页
    if (currentPage.value > totalPages.value) {
      currentPage.value = Math.max(1, totalPages.value)
    }
  }
}

// 清空照片墙
function clearPhotoWall() {
  if (confirm('确定要清空整个照片墙吗？此操作不可恢复。')) {
    photoWall.value = []
    localStorage.setItem('photoWall', '[]')
    selectedImages.value = []
    currentPage.value = 1
  }
}

// 切换分页
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

// 切换布局模式
function changeLayoutMode(mode) {
  layoutMode.value = mode
}

// 切换控制栏显示
function toggleControls() {
  showControls.value = !showControls.value
}
</script>

<template>
  <!-- 照片墙页面 -->
  <section id="photo-wall" class="mb-12">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover-scale">
      <div class="flex flex-wrap justify-between items-center mb-6 gap-4">
        <h2 class="text-2xl font-bold">照片墙</h2>
        <div class="flex items-center space-x-2">
          <button 
            class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            @click="toggleControls"
            title="切换控制栏"
          >
            <i class="fa fa-sliders"></i>
          </button>
          <span class="text-sm text-gray-500 dark:text-gray-400">{{ photoWall.length }} 张图片</span>
        </div>
      </div>
      
      <!-- 控制栏 -->
      <div v-if="showControls" class="mb-6 p-4 bg-gray-100 dark:bg-gray-700/50 rounded-lg">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- 显示数量设置 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">每页显示数量</label>
            <div class="flex space-x-2">
              <select 
                v-model.number="pageSize" 
                class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary/50 focus:border-primary outline-none"
              >
                <option :value="12">12</option>
                <option :value="24">24</option>
                <option :value="36">36</option>
                <option :value="48">48</option>
                <option :value="60">60</option>
              </select>
            </div>
          </div>
          
          <!-- 布局模式设置 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">布局模式</label>
            <div class="flex space-x-2">
              <button 
                class="flex-1 px-4 py-2 rounded-lg transition-colors flex items-center justify-center"
                :class="layoutMode === 'grid' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'"
                @click="changeLayoutMode('grid')"
              >
                <i class="fa fa-th mr-2"></i>网格
              </button>
              <button 
                class="flex-1 px-4 py-2 rounded-lg transition-colors flex items-center justify-center"
                :class="layoutMode === 'masonry' ? 'bg-primary text-white' : 'bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600'"
                @click="changeLayoutMode('masonry')"
              >
                <i class="fa fa-th-large mr-2"></i>瀑布流
              </button>
            </div>
          </div>
          
          <!-- 批量操作 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">批量操作</label>
            <div class="flex space-x-2">
              <button 
                class="flex-1 px-4 py-2 bg-danger text-white rounded-lg hover:bg-danger/90 transition-colors flex items-center justify-center"
                @click="batchDelete"
                :disabled="selectedImages.length === 0"
              >
                <i class="fa fa-trash mr-2"></i>删除 ({{ selectedImages.length }})
              </button>
              <button 
                class="flex-1 px-4 py-2 bg-warning text-white rounded-lg hover:bg-warning/90 transition-colors flex items-center justify-center"
                @click="clearPhotoWall"
                :disabled="photoWall.length === 0"
              >
                <i class="fa fa-refresh mr-2"></i>清空
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 照片墙内容 -->
      <div class="mb-6">
        <!-- 全选和分页信息 -->
        <div class="flex flex-wrap justify-between items-center mb-4 gap-2">
          <div class="flex items-center space-x-2">
            <input 
              type="checkbox" 
              id="select-all-photos" 
              class="rounded text-primary focus:ring-primary/50"
              @change="toggleSelectAll"
              :checked="selectedImages.length === paginatedPhotos.length && paginatedPhotos.length > 0"
            >
            <label for="select-all-photos" class="text-sm text-gray-700 dark:text-gray-300">全选</label>
            <span class="text-sm text-gray-500 dark:text-gray-400">({{ selectedImages.length }} / {{ paginatedPhotos.length }})</span>
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400">
            第 {{ currentPage }} / {{ totalPages }} 页
          </div>
        </div>
        
        <!-- 网格布局 -->
        <div v-if="layoutMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          <div 
            v-for="photo in paginatedPhotos" 
            :key="photo.id"
            class="relative group"
          >
            <!-- 图片卡片 -->
            <div class="bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-all">
              <div class="relative aspect-square overflow-hidden">
                <img 
                  :src="photo.thumbnail" 
                  :alt="photo.filename" 
                  class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                >
                
                <!-- 选择复选框 -->
                <div class="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <input 
                    type="checkbox" 
                    :id="`select-photo-${photo.id}`"
                    class="rounded text-primary focus:ring-primary/50"
                    :checked="selectedImages.includes(photo.id)"
                    @change="toggleImageSelection(photo.id)"
                  >
                </div>
                
                <!-- 图片信息 -->
                <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-end">
                  <div class="p-3 w-full">
                    <p class="text-white text-sm truncate">{{ photo.filename }}</p>
                    <p class="text-gray-300 text-xs">{{ photo.size }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 瀑布流布局 -->
        <div v-else-if="layoutMode === 'masonry'" class="columns-2 sm:columns-3 md:columns-4 lg:columns-5 gap-4">
          <div 
            v-for="photo in paginatedPhotos" 
            :key="photo.id"
            class="relative break-inside-avoid mb-4"
          >
            <!-- 图片卡片 -->
            <div class="bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow-md hover:shadow-lg transition-all">
              <div class="relative">
                <img 
                  :src="photo.url" 
                  :alt="photo.filename" 
                  class="w-full rounded-t-lg"
                  style="height: auto;"
                >
                
                <!-- 选择复选框 -->
                <div class="absolute top-2 left-2 opacity-0 hover:opacity-100 transition-opacity">
                  <input 
                    type="checkbox" 
                    :id="`select-photo-${photo.id}`"
                    class="rounded text-primary focus:ring-primary/50"
                    :checked="selectedImages.includes(photo.id)"
                    @change="toggleImageSelection(photo.id)"
                  >
                </div>
                
                <!-- 图片信息 -->
                <div class="p-3 bg-white dark:bg-gray-800">
                  <p class="text-sm font-medium truncate">{{ photo.filename }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400">{{ photo.size }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 空状态 -->
        <div v-if="paginatedPhotos.length === 0" class="text-center py-12">
          <div class="w-16 h-16 mx-auto mb-4 text-gray-400">
            <i class="fa fa-picture-o text-4xl"></i>
          </div>
          <h3 class="text-lg font-semibold mb-2">照片墙为空</h3>
          <p class="text-gray-500 dark:text-gray-400">
            从结果管理页面选择图片添加到照片墙
          </p>
        </div>
      </div>
      
      <!-- 分页控件 -->
      <div v-if="totalPages > 1" class="flex justify-center items-center space-x-2">
        <button 
          class="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          @click="prevPage"
          :disabled="currentPage === 1"
        >
          <i class="fa fa-chevron-left mr-2"></i>上一页
        </button>
        <span class="text-sm text-gray-700 dark:text-gray-300">
          {{ currentPage }} / {{ totalPages }}
        </span>
        <button 
          class="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          @click="nextPage"
          :disabled="currentPage === totalPages"
        >
          下一页 <i class="fa fa-chevron-right ml-2"></i>
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 组件特定样式 */
/* 瀑布流布局样式 */
.columns-2 {
  column-count: 2;
}

.columns-3 {
  column-count: 3;
}

.columns-4 {
  column-count: 4;
}

.columns-5 {
  column-count: 5;
}

.break-inside-avoid {
  break-inside: avoid;
}

/* 图片加载动画 */
.img-loading {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>