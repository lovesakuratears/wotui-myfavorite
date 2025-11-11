// 模拟数据文件，用于前端展示示例数据

// 示例任务数据
const mockTasks = [
    {
        id: 'task_1716214800000',
        type: '快速执行',
        status: 'completed',
        statusText: '已完成',
        startTime: '2024-05-20 14:30:22',
        endTime: '2024-05-20 14:45:36',
        progress: 100,
        userIds: ['1669879400'],
        count: 50
    },
    {
        id: 'task_1716128400000',
        type: '定时执行',
        status: 'completed',
        statusText: '已完成',
        startTime: '2024-05-19 10:15:00',
        endTime: '2024-05-19 10:30:15',
        progress: 100,
        userIds: ['1729370543'],
        count: 42
    },
    {
        id: 'task_1716042000000',
        type: '批量执行',
        status: 'completed',
        statusText: '已完成',
        startTime: '2024-05-18 09:00:00',
        endTime: '2024-05-18 09:45:20',
        progress: 100,
        userIds: ['1669879400', '1729370543'],
        count: 89
    },
    {
        id: 'task_1715955600000',
        type: '快速执行',
        status: 'failed',
        statusText: '失败',
        startTime: '2024-05-17 16:20:00',
        endTime: '2024-05-17 16:22:10',
        progress: 0,
        userIds: ['1234567890'],
        count: 0,
        error: '用户ID不存在'
    }
];

// 示例文件数据
const mockFiles = [
    {
        id: '1',
        name: 'Dear-迪丽热巴',
        type: 'folder',
        size: null,
        modifiedTime: '2024-05-20 14:30:00',
        userDir: true
    },
    {
        id: '2',
        name: '郭碧婷',
        type: 'folder',
        size: null,
        modifiedTime: '2024-05-19 10:15:00',
        userDir: true
    },
    {
        id: '3',
        name: 'weibo_data.csv',
        type: 'file',
        extension: 'csv',
        size: '2.5 MB',
        modifiedTime: '2024-05-20 14:45:00'
    },
    {
        id: '4',
        name: 'weibo_data.json',
        type: 'file',
        extension: 'json',
        size: '3.2 MB',
        modifiedTime: '2024-05-19 10:30:00'
    },
    {
        id: '5',
        name: 'media',
        type: 'folder',
        size: null,
        modifiedTime: '2024-05-18 09:45:00'
    }
];

// 示例日志数据
const mockLogs = [
    {
        time: '2024-05-20 14:30:22',
        level: 'INFO',
        message: '开始爬取用户 1669879400 的微博'
    },
    {
        time: '2024-05-20 14:30:25',
        level: 'INFO',
        message: '成功获取用户信息: Dear-迪丽热巴'
    },
    {
        time: '2024-05-20 14:30:30',
        level: 'INFO',
        message: '已爬取 20 条微博'
    },
    {
        time: '2024-05-20 14:30:35',
        level: 'DEBUG',
        message: '下载图片: https://wx3.sinaimg.cn/large/006XXwaCgy1h3l6z7j8ooj30sg0sg43q.jpg'
    },
    {
        time: '2024-05-20 14:30:40',
        level: 'DEBUG',
        message: '下载图片: https://wx4.sinaimg.cn/large/006XXwaCgy1h3l6z8g7k3j30sg0sg42l.jpg'
    },
    {
        time: '2024-05-20 14:30:45',
        level: 'DEBUG',
        message: '下载图片: https://wx1.sinaimg.cn/large/006XXwaCgy1h3l6z9f6e7j30sg0sg75j.jpg'
    },
    {
        time: '2024-05-20 14:31:00',
        level: 'INFO',
        message: '已爬取 40 条微博'
    },
    {
        time: '2024-05-20 14:31:10',
        level: 'INFO',
        message: '爬取完成，共获取 50 条微博'
    },
    {
        time: '2024-05-20 14:31:15',
        level: 'INFO',
        message: '开始处理媒体文件'
    },
    {
        time: '2024-05-20 14:31:30',
        level: 'INFO',
        message: '媒体文件处理完成，共下载 15 张图片'
    },
    {
        time: '2024-05-20 14:31:35',
        level: 'INFO',
        message: '开始保存到CSV文件'
    },
    {
        time: '2024-05-20 14:31:40',
        level: 'INFO',
        message: 'CSV文件保存完成: ./weibo_data.csv'
    },
    {
        time: '2024-05-20 14:45:36',
        level: 'INFO',
        message: '任务 task_1716214800000 执行完成'
    }
];

// 示例统计数据
const mockStats = {
    userCount: 12,
    weiboCount: 1245,
    mediaCount: 368,
    successRate: '98.5%',
    userCountChange: '+15%',
    weiboCountChange: '+23%',
    mediaCountChange: '+8%',
    successRateChange: '-1.2%'
};

// 模拟API响应函数
function mockApiResponse(data, delay = 300) {
    return new Promise(resolve => {
        setTimeout(() => resolve(data), delay);
    });
}

// 导出模拟数据
window.mockData = {
    tasks: mockTasks,
    files: mockFiles,
    logs: mockLogs,
    stats: mockStats,
    getTasks: () => mockApiResponse(mockTasks),
    getFiles: () => mockApiResponse(mockFiles),
    getLogs: () => mockApiResponse(mockLogs),
    getStats: () => mockApiResponse(mockStats)
};

// 加载完成时更新任务列表
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        // 尝试更新任务列表
        const taskList = document.getElementById('task-list');
        if (taskList) {
            window.mockData.getTasks().then(tasks => {
                let html = '';
                tasks.forEach(task => {
                    const statusClass = task.status === 'completed' ? 
                        'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100' : 
                        task.status === 'failed' ? 
                        'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100' : 
                        'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100';
                    
                    html += `
                    <tr class="border-b border-gray-200 dark:border-gray-700">
                        <td class="py-3 px-4 text-sm">${task.id}</td>
                        <td class="py-3 px-4 text-sm">${task.type}</td>
                        <td class="py-3 px-4 text-sm">
                            <span class="px-2 py-1 ${statusClass} rounded text-xs">${task.statusText}</span>
                        </td>
                        <td class="py-3 px-4 text-sm">${task.startTime}</td>
                        <td class="py-3 px-4 text-sm">${task.endTime}</td>
                        <td class="py-3 px-4 text-sm">
                            <div class="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-600">
                                <div class="bg-primary h-2 rounded-full" style="width: ${task.progress}%"></div>
                            </div>
                        </td>
                        <td class="py-3 px-4 text-sm">
                            <button class="text-primary hover:text-primary/80 mr-2">
                                <i class="fa fa-eye"></i>
                            </button>
                            <button class="text-secondary hover:text-secondary/80">
                                <i class="fa fa-download"></i>
                            </button>
                        </td>
                    </tr>
                    `;
                });
                taskList.innerHTML = html;
            });
        }
        
        // 尝试更新文件列表
        const fileList = document.getElementById('file-list');
        if (fileList) {
            window.mockData.getFiles().then(files => {
                let html = '';
                files.forEach(file => {
                    const iconClass = file.type === 'folder' ? 
                        'fa fa-folder-o text-yellow-500' : 
                        file.extension === 'csv' ? 
                        'fa fa-file-excel-o text-green-500' : 
                        file.extension === 'json' ? 
                        'fa fa-file-code-o text-blue-500' : 
                        'fa fa-file-o text-gray-500';
                    
                    html += `
                    <tr class="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
                        <td class="py-3 px-4 text-sm">
                            <div class="flex items-center">
                                <i class="${iconClass} mr-2"></i>
                                <span>${file.name}</span>
                            </div>
                        </td>
                        <td class="py-3 px-4 text-sm">${file.type === 'folder' ? '文件夹' : '文件'}</td>
                        <td class="py-3 px-4 text-sm">${file.size || '--'}</td>
                        <td class="py-3 px-4 text-sm">${file.modifiedTime}</td>
                        <td class="py-3 px-4 text-sm">
                            ${file.type === 'folder' ? 
                                `<button class="text-primary hover:text-primary/80 mr-2">
                                    <i class="fa fa-folder-open-o"></i>
                                </button>` : 
                                ''
                            }
                            <button class="text-secondary hover:text-secondary/80">
                                <i class="fa fa-download"></i>
                            </button>
                        </td>
                    </tr>
                    `;
                });
                fileList.innerHTML = html;
            });
        }
        
        // 尝试更新日志内容
        const logContent = document.getElementById('logs-content');
        if (logContent) {
            window.mockData.getLogs().then(logs => {
                let html = '';
                logs.forEach(log => {
                    const levelClass = log.level === 'INFO' ? 
                        'text-green-600 dark:text-green-400' : 
                        log.level === 'DEBUG' ? 
                        'text-blue-600 dark:text-blue-400' : 
                        log.level === 'ERROR' ? 
                        'text-red-600 dark:text-red-400' : 
                        'text-gray-600 dark:text-gray-400';
                    
                    html += `<p class="${levelClass}">[${log.time}] ${log.level}: ${log.message}</p>`;
                });
                logContent.innerHTML = html;
                logContent.scrollTop = logContent.scrollHeight;
            });
        }
    });
}