// 查找任务进度区域，添加停止按钮
function addStopTaskButton() {
    const taskProgressDiv = document.getElementById('taskProgress');
    if (taskProgressDiv) {
        // 检查是否已存在停止按钮
        if (!document.getElementById('stopTaskBtn')) {
            const stopBtn = document.createElement('button');
            stopBtn.id = 'stopTaskBtn';
            stopBtn.className = 'btn btn-danger';
            stopBtn.textContent = '停止爬取';
            stopBtn.onclick = stopCrawlingTask;
            stopBtn.style.marginLeft = '10px';
            
            // 找到进度条后插入按钮
            const progressBar = taskProgressDiv.querySelector('.progress');
            if (progressBar) {
                taskProgressDiv.insertBefore(stopBtn, progressBar.nextSibling);
            }
        }
    }
}

// 停止爬取任务的函数
function stopCrawlingTask() {
    if (!currentTaskId) {
        showMessage('没有正在运行的任务', 'warning');
        return;
    }
    
    // 更新UI状态
    document.getElementById('stopTaskBtn').disabled = true;
    showMessage('正在停止任务...', 'info');
    
    // 发送停止请求
    fetch('/task/cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('任务已停止', 'success');
            // 重置当前任务ID
            currentTaskId = null;
            localStorage.removeItem('currentTaskId');
            // 更新UI状态
            updateUIWithTaskStatus({state: 'CANCELED', progress: 0});
        } else {
            showMessage('停止任务失败: ' + (data.error || '未知错误'), 'error');
            document.getElementById('stopTaskBtn').disabled = false;
        }
    })
    .catch(error => {
        console.error('停止任务出错:', error);
        showMessage('停止任务时发生错误', 'error');
        document.getElementById('stopTaskBtn').disabled = false;
    });
}

// 修改updateUIWithTaskStatus函数，处理停止状态
function updateUIWithTaskStatus(taskStatus) {
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('statusText');
    const stopTaskBtn = document.getElementById('stopTaskBtn');
    
    if (!progressBar || !statusText) return;
    
    // 更新进度条
    progressBar.style.width = taskStatus.progress + '%';
    progressBar.setAttribute('aria-valuenow', taskStatus.progress);
    progressBar.textContent = taskStatus.progress + '%';
    
    // 更新状态文本
    let statusMessage = '';
    let progressClass = '';
    
    switch (taskStatus.state) {
        case 'PENDING':
            statusMessage = '任务等待中...';
            progressClass = 'bg-warning';
            break;
        case 'PROGRESS':
            statusMessage = '任务进行中...';
            progressClass = 'bg-info';
            // 启用停止按钮
            if (stopTaskBtn) stopTaskBtn.disabled = false;
            break;
        case 'COMPLETED':
            statusMessage = '任务已完成';
            progressClass = 'bg-success';
            // 禁用停止按钮
            if (stopTaskBtn) stopTaskBtn.disabled = true;
            // 重置当前任务ID
            currentTaskId = null;
            localStorage.removeItem('currentTaskId');
            break;
        case 'FAILED':
            statusMessage = '任务失败: ' + (taskStatus.error || '未知错误');
            progressClass = 'bg-danger';
            // 禁用停止按钮
            if (stopTaskBtn) stopTaskBtn.disabled = true;
            // 重置当前任务ID
            currentTaskId = null;
            localStorage.removeItem('currentTaskId');
            break;
        case 'CANCELED':
            statusMessage = '任务已取消';
            progressClass = 'bg-secondary';
            // 禁用停止按钮
            if (stopTaskBtn) stopTaskBtn.disabled = true;
            break;
        default:
            statusMessage = '未知状态';
            progressClass = 'bg-secondary';
    }
    
    statusText.textContent = statusMessage;
    
    // 更新进度条样式
    // 移除所有进度条类
    progressBar.className = progressBar.className.replace(/bg-\w+/g, '');
    // 添加新的进度条类
    progressBar.classList.add(progressClass);
    
    // 显示任务进度区域
    document.getElementById('taskProgress').style.display = 'block';
}

// 在页面加载完成后添加停止按钮
document.addEventListener('DOMContentLoaded', function() {
    addStopTaskButton();
});
