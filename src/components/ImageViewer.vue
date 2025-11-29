<script setup>
import { ref, onMounted, computed } from 'vue'

// 定义属性和事件
const props = defineProps({
  user: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])

// 图片数据
const images = ref([])
const currentImageIndex = ref(0)
const selectedImages = ref([])
const showThumbnails = ref(true)

// 分页设置
const pageSize = ref(9)
const currentPage = ref(1)

// 计算属性
const currentImage = computed(() => {
  return images.value[currentImageIndex.value] || null
})

const totalPages = computed(() => {
  return Math.ceil(images.value.length / pageSize.value)
})

const paginatedImages = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return images.value.slice(start, end)
})

// 初始化图片数据
onMounted(() => {
  loadMockImages()
})

// 加载模拟图片数据
function loadMockImages() {
  // 模拟用户图片数据
  const mockImages = []
  for (let i = 1; i <= props.user.imageCount; i++) {
    mockImages.push({
      id: `${props.user.id}_${i}`,
      url: `https://picsum.photos/800/600?random=${props.user.id}_${i}`,
      thumbnail: `https://picsum.photos/100/100?random=${props.user.id}_${i}`,
      filename: `${props.user.id}_image_${i}.jpg`,
      size: `${Math.floor(Math.random() * 5) + 1}.${Math.floor(Math.random() * 100).toString().padStart(2, '0')} MB`,
      created: new Date().toISOString()
    })
  }
  images.value = mockImages
}

// 切换图片
function prevImage() {
  if (currentImageIndex.value > 0) {
    currentImageIndex.value--
  }
}

function nextImage() {
  if (currentImageIndex.value < images.value.length - 1) {
    currentImageIndex.value++
  }
}

// 跳转到指定图片
function goToImage(index) {
  currentImageIndex.value = index
}

// 下载当前图片
function downloadCurrentImage() {
  if (!currentImage.value) return
  
  const link = document.createElement('a')
  link.href = currentImage.value.url
  link.download = currentImage.value.filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
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
  if (selectedImages.value.length === paginatedImages.value.length) {
    selectedImages.value = []
  } else {
    selectedImages.value = paginatedImages.value.map(img => img.id)
  }
}

// 批量下载
function batchDownload() {
  if (selectedImages.value.length === 0) {
    alert('请先选择要下载的图片')
    return
  }
  
  console.log('批量下载图片:', selectedImages.value)
  alert(`正在下载 ${selectedImages.value.length} 张图片...`)
}

// 批量删除
function batchDelete() {
  if (selectedImages.value.length === 0) {
    alert('请先选择要删除的图片')
    return
  }
  
  if (confirm(`确定要删除选中的 ${selectedImages.value.length} 张图片吗？`)) {
    images.value = images.value.filter(img => !selectedImages.value.includes(img.id))
    selectedImages.value = []
    if (currentImageIndex.value >= images.value.length) {
      currentImageIndex.value = Math.max(0, images.value.length - 1)
    }
  }
}

// 添加到照片墙
function addToPhotoWall() {
  if (selectedImages.value.length === 0) {
    alert('请先选择要添加到照片墙的图片')
    return
  }
  
  // 获取选中的图片
  const selectedImagesData = images.value.filter(img => selectedImages.value.includes(img.id))
  
  // 从localStorage获取现有照片墙数据
  const photoWallData = JSON.parse(localStorage.getItem('photoWall') || '[]')
  
  // 添加新图片到照片墙
  const updatedPhotoWall = [...photoWallData, ...selectedImagesData]
  localStorage.setItem('photoWall', JSON.stringify(updatedPhotoWall))
  
  alert(`已将 ${selectedImages.value.length} 张图片添加到照片墙`)
}

// 切换缩略图显示
function toggleThumbnailsVisibility() {
  showThumbnails.value = !showThumbnails.value
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

// 关闭图片查看器
function closeViewer() {
  emit('close')
}
</script>

<template>
  <!-- 图片查看器背景 -->
  <div class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
    <!-- 图片查看器容器 -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-7xl max-h-[90vh] overflow-hidden flex flex-col">
      <!-- 顶部工具栏 -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-white dark:bg-gray-800/95 backdrop-blur-sm">
        <div class="flex items-center space-x-2">
          <h3 class="text-lg font-semibold">{{ user.name }} 的图片 ({{ images.length }} 张)</h3>
          <span class="text-sm text-gray-500 dark:text-gray-400">({{ currentImageIndex + 1 }} / {{ images.length }})</span>
        </div>
        <div class="flex items-center space-x-2">
          <button 
            class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            @click="toggleThumbnailsVisibility"
            title="切换缩略图"
          >
            <i class="fa fa-th-large"></i>
          </button>
          <button 
            class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            @click="closeViewer"
            title="关闭"
          >
            <i class="fa fa-times"></i>
          </button>
        </div>
      </div>
      
      <!-- 图片查看区域 -->
      <div class="flex-1 flex items-center justify-center p-4 bg-gray-900 relative">
        <!-- 上一张/下一张按钮 -->
        <button 
          class="absolute left-4 top-1/2 transform -translate-y-1/2 bg-white/20 hover:bg-white/30 text-white p-3 rounded-full transition-all z-10"
          @click="prevImage"
          :disabled="currentImageIndex === 0"
        >
          <i class="fa fa-chevron-left text-xl"></i>
        </button>
        
        <button 
          class="absolute right-4 top-1/2 transform -translate-y-1/2 bg-white/20 hover:bg-white/30 text-white p-3 rounded-full transition-all z-10"
          @click="nextImage"
          :disabled="currentImageIndex === images.length - 1"
        >
          <i class="fa fa-chevron-right text-xl"></i>
        </button>
        
        <!-- 当前图片 -->
        <div v-if="currentImage" class="max-w-full max-h-[60vh] flex items-center justify-center">
          <img 
            :src="currentImage.url" 
            :alt="currentImage.filename" 
            class="max-w-full max-h-full object-contain rounded-lg shadow-lg"
          >
        </div>
        <div v-else class="text-white text-xl">
          暂无图片
        </div>
        
        <!-- 图片信息 -->
        <div class="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black/70 text-white px-4 py-2 rounded-full text-sm">
          {{ currentImage?.filename }} ({{ currentImage?.size }})
        </div>
      </div>
      
      <!-- 图片操作栏 -->
      <div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/95 backdrop-blur-sm">
        <div class="flex flex-wrap justify-between items-center gap-2">
          <!-- 单张图片操作 -->
          <div class="flex space-x-2">
            <button 
              class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors flex items-center"
              @click="downloadCurrentImage"
              :disabled="!currentImage"
            >
              <i class="fa fa-download mr-2"></i>下载当前
            </button>
            <button 
              class="px-4 py-2 bg-success text-white rounded-lg hover:bg-success/90 transition-colors flex items-center"
              @click="toggleImageSelection(currentImage?.id)"
              :disabled="!currentImage"
            >
              <i class="fa fa-star mr-2"></i>
              {{ selectedImages.includes(currentImage?.id) ? '取消收藏' : '收藏' }}
            </button>
          </div>
          
          <!-- 批量操作 -->
          <div class="flex space-x-2">
            <button 
              class="px-4 py-2 bg-info text-white rounded-lg hover:bg-info/90 transition-colors flex items-center"
              @click="batchDownload"
              :disabled="selectedImages.length === 0"
            >
              <i class="fa fa-download mr-2"></i>批量下载 ({{ selectedImages.length }})
            </button>
            <button 
              class="px-4 py-2 bg-danger text-white rounded-lg hover:bg-danger/90 transition-colors flex items-center"
              @click="batchDelete"
              :disabled="selectedImages.length === 0"
            >
              <i class="fa fa-trash mr-2"></i>批量删除 ({{ selectedImages.length }})
            </button>
            <button 
              class="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors flex items-center"
              @click="addToPhotoWall"
              :disabled="selectedImages.length === 0"
            >
              <i class="fa fa-th mr-2"></i>添加到照片墙
            </button>
          </div>
        </div>
      </div>
      
      <!-- 缩略图区域 -->
      <div v-if="showThumbnails" class="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/95 backdrop-blur-sm">
        <!-- 缩略图工具栏 -->
        <div class="p-2 flex justify-between items-center bg-gray-100 dark:bg-gray-700/50">
          <div class="flex items-center space-x-2">
            <input 
              type="checkbox" 
              id="select-all" 
              class="rounded text-primary focus:ring-primary/50"
              @change="toggleSelectAll"
              :checked="selectedImages.length === paginatedImages.length && paginatedImages.length > 0"
            >
            <label for="select-all" class="text-sm text-gray-700 dark:text-gray-300">全选</label>
            <span class="text-sm text-gray-500 dark:text-gray-400">({{ selectedImages.length }} / {{ paginatedImages.length }})</span>
          </div>
          
          <!-- 分页设置 -->
          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-700 dark:text-gray-300">每页显示:</span>
            <select 
              v-model.number="pageSize" 
              class="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
            >
              <option :value="6">6</option>
              <option :value="9">9</option>
              <option :value="12">12</option>
              <option :value="18">18</option>
              <option :value="24">24</option>
            </select>
            <span class="text-sm text-gray-700 dark:text-gray-300">张</span>
          </div>
        </div>
        
        <!-- 缩略图列表 -->
        <div class="p-4 overflow-x-auto">
          <div class="flex space-x-3">
            <div 
              v-for="(image, index) in paginatedImages" 
              :key="image.id"
              class="relative cursor-pointer transition-all hover:scale-105"
              @click="goToImage(images.indexOf(image))"
            >
              <!-- 缩略图 -->
              <img 
                :src="image.thumbnail" 
                :alt="image.filename" 
                class="w-20 h-20 object-cover rounded-lg border-2 transition-all"
                :class="{
                  'border-primary': images.indexOf(image) === currentImageIndex,
                  'border-gray-300': images.indexOf(image) !== currentImageIndex
                }"
              >
              
              <!-- 选择复选框 -->
              <div class="absolute top-1 right-1">
                <input 
                  type="checkbox" 
                  :id="`select-${image.id}`"
                  class="rounded text-primary focus:ring-primary/50"
                  :checked="selectedImages.includes(image.id)"
                  @change="toggleImageSelection(image.id)"
                  @click.stop
                >
              </div>
              
              <!-- 当前图片标记 -->
              <div 
                v-if="images.indexOf(image) === currentImageIndex"
                class="absolute bottom-1 left-1/2 transform -translate-x-1/2 bg-primary text-white text-xs px-2 py-0.5 rounded-full"
              >
                当前
              </div>
            </div>
          </div>
        </div>
        
        <!-- 分页控件 -->
        <div class="p-2 flex justify-center items-center space-x-2 bg-gray-100 dark:bg-gray-700/50">
          <button 
            class="px-3 py-1 rounded-lg bg-white dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            @click="prevPage"
            :disabled="currentPage === 1"
          >
            <i class="fa fa-chevron-left"></i>
          </button>
          <span class="text-sm text-gray-700 dark:text-gray-300">
            {{ currentPage }} / {{ totalPages }}
          </span>
          <button 
            class="px-3 py-1 rounded-lg bg-white dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            @click="nextPage"
            :disabled="currentPage === totalPages"
          >
            <i class="fa fa-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 组件特定样式 */
.thumbnail-loading {
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