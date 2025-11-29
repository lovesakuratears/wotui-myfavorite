from weibo import Weibo, handle_config_renaming
import const
import logging
import logging.config
import os
import json
import uuid
import logging
import logging.config
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
import sqlite3
from concurrent.futures import ThreadPoolExecutor

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建数据目录
os.makedirs(os.path.join(BASE_DIR, 'weibo'), exist_ok=True)

# 数据库路径
DATABASE_PATH = os.path.join(BASE_DIR, 'weibo', 'weibodata.db')
print(f"数据库路径: {DATABASE_PATH}")

# 配置日志
if not os.path.isdir("log/"):
    os.makedirs("log/")
logging_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + "logging.conf"
logging.config.fileConfig(logging_path)
logger = logging.getLogger("api")

# 全局变量
config = {}

# 默认配置
DEFAULT_CONFIG = {
    "user_id_list": [],
    "query_list": "",
    "only_crawl_original": 1,
    "since_date": 1,
    "start_page": 1,
    "write_mode": ["csv", "sqlite"],
    "original_pic_download": 0,
    "retweet_pic_download": 0,
    "original_video_download": 0,
    "retweet_video_download": 0,
    "original_live_photo_download": 0,
    "retweet_live_photo_download": 0,
    "download_comment": 0,
    "comment_max_download_count": 100,
    "download_repost": 0,
    "repost_max_download_count": 100,
    "user_id_as_folder_name": 0,
    "remove_html_tag": 1,
    "cookie": "",
    "mysql_config": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "123456",
        "charset": "utf8mb4"
    },
    "mongodb_URI": "",
    "post_config": {
        "api_url": "",
        "api_token": ""
    }
}

# 创建Flask应用
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # 添加CORS支持，允许所有来源的跨域请求

# 配置Flask
app.static_folder = os.path.join(BASE_DIR, 'static')
app.template_folder = BASE_DIR
app.config['JSON_AS_ASCII'] = False  # 确保JSON响应中的中文不会被转义
app.config['JSONIFY_MIMETYPE'] = 'application/json;charset=utf-8'

# 线程池和任务管理
executor = ThreadPoolExecutor(max_workers=1)  # 限制只有1个worker避免并发爬取
tasks = {}
task_creation_lock = threading.Lock()  # 用于确保任务ID的唯一性
current_task_id = None
task_lock = threading.Lock()

# 任务状态文件路径
TASKS_FILE_PATH = os.path.join(BASE_DIR, 'tasks_state.json')

# 定时任务配置
schedule_config = {
    "enabled": False,
    "interval": "daily",  # options: hourly, daily, weekly, custom
    "custom_interval": 60  # in minutes, used when interval is "custom"
}

# 配置文件路径
CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.json')

# 获取当前正在运行的任务
def get_running_task():
    global current_task_id
    with task_lock:
        if current_task_id and current_task_id in tasks:
            return current_task_id, tasks[current_task_id]
        return None, None

# 获取配置
def get_config(user_id_list=None):
    """获取配置，如果提供了user_id_list则覆盖配置中的user_id_list"""
    if not config:
        load_config_file()
    
    # 创建配置副本
    task_config = config.copy()
    
    # 如果提供了user_id_list，则覆盖配置中的user_id_list
    if user_id_list:
        task_config['user_id_list'] = user_id_list
    
    return task_config

# 运行刷新任务
def run_refresh_task(task_id, user_id_list=None):
    """运行微博数据刷新任务"""
    def log_message(message, level='info'):
        """记录日志到任务中并保存状态"""
        try:
            with task_lock:
                if task_id in tasks and isinstance(tasks[task_id], dict):
                    if 'logs' not in tasks[task_id]:
                        tasks[task_id]['logs'] = []
                    tasks[task_id]['logs'].append({
                        'timestamp': datetime.now().isoformat(),
                        'level': level,
                        'message': message
                    })
                    tasks[task_id]['last_activity_time'] = datetime.now().isoformat()
                    save_tasks_state()
                    logger.info(f"任务 {task_id} 日志: {message}")
        except Exception as e:
            logger.exception(f"记录日志失败: {e}")
    
    try:
        # 获取配置
        log_message("开始处理任务配置")
        task_config = get_config(user_id_list)
        
        # 初始化任务状态为进行中
        with task_lock:
            if task_id in tasks and isinstance(tasks[task_id], dict):
                tasks[task_id]['state'] = 'PROGRESS'
                tasks[task_id]['start_time'] = datetime.now().isoformat()
                tasks[task_id]['last_activity_time'] = datetime.now().isoformat()
                save_tasks_state()
        
        log_message("配置处理完成，准备创建微博爬取对象")
        
        # 创建进度更新线程
        def update_progress():
            while True:
                try:
                    with task_lock:
                        if task_id not in tasks or not isinstance(tasks[task_id], dict) or tasks[task_id]['state'] not in ['PROGRESS', 'PENDING']:
                            break
                        tasks[task_id]['last_activity_time'] = datetime.now().isoformat()
                        # 逐步增加进度，而不是随机值
                        current_progress = tasks[task_id].get('progress', 0)
                        if current_progress < 95:
                            tasks[task_id]['progress'] = min(current_progress + 1, 95)
                        save_tasks_state()
                except Exception as e:
                    logger.exception(f"更新进度失败: {e}")
                time.sleep(3)  # 每3秒更新一次，更频繁
        
        progress_thread = threading.Thread(target=update_progress)
        progress_thread.daemon = True
        progress_thread.start()
        
        log_message("处理配置重命名")
        # 处理配置重命名
        task_config = handle_config_renaming(task_config)
        
        log_message("配置处理完成，准备创建微博爬取对象")
        
        # 创建微博对象
        wb = Weibo(task_config)
        
        log_message("微博爬取对象创建完成，准备开始执行爬取任务")
        
        # 设置任务超时时间（例如2小时）
        timeout = 2 * 60 * 60  # 2小时
        start_time = time.time()
        
        log_message("开始执行爬取任务")
        
        # 执行爬取任务
        log_message("正在执行爬取操作...")
        wb.run()
        
        log_message("爬取任务执行完成")
        
        # 更新任务状态为完成
        with task_lock:
            if task_id in tasks and isinstance(tasks[task_id], dict):
                tasks[task_id]['state'] = 'COMPLETED'
                tasks[task_id]['progress'] = 100
                tasks[task_id]['last_activity_time'] = datetime.now().isoformat()
                tasks[task_id]['result'] = "爬取完成"
                log_message("任务执行成功，已完成所有爬取操作")
                save_tasks_state()
    except Exception as e:
        error_msg = f"任务执行失败: {str(e)}"
        logger.exception(f"任务 {task_id} 执行失败")
        # 更新任务状态为失败
        with task_lock:
            if task_id in tasks and isinstance(tasks[task_id], dict):
                tasks[task_id]['state'] = 'FAILED'
                tasks[task_id]['progress'] = 0
                tasks[task_id]['last_activity_time'] = datetime.now().isoformat()
                tasks[task_id]['error'] = str(e)
                log_message(error_msg, 'error')
                save_tasks_state()
    finally:
        # 确保进度更新线程停止
        try:
            progress_thread.join(timeout=1)  # 等待进度线程结束，最多等待1秒
        except Exception:
            pass
        
        # 最后保存一次任务状态
        with task_lock:
            if task_id in tasks and isinstance(tasks[task_id], dict):
                save_tasks_state()
                # 如果当前任务已结束，清除当前任务ID
                global current_task_id
                if current_task_id == task_id:
                    current_task_id = None

# 保存任务状态到文件
def save_tasks_state():
    """保存任务状态到文件"""
    try:
        with open(TASKS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("保存任务状态失败")

# 从文件加载任务状态
def load_tasks_state():
    """从文件加载任务状态"""
    global tasks
    try:
        if os.path.exists(TASKS_FILE_PATH):
            with open(TASKS_FILE_PATH, 'r', encoding='utf-8') as f:
                loaded_tasks = json.load(f)
                
                # 过滤掉旧任务（超过24小时）
                current_time = time.time()
                filtered_tasks = {}
                for task_id, task in loaded_tasks.items():
                    # 确保task是字典类型
                    if not isinstance(task, dict):
                        continue
                    
                    # 检查任务创建时间
                    created_time_str = task.get('created_at', '1970-01-01T00:00:00.000Z')
                    try:
                        created_time = datetime.fromisoformat(created_time_str.replace('Z', '+00:00')).timestamp()
                        if current_time - created_time < 24 * 60 * 60:  # 24小时内的任务保留
                            filtered_tasks[task_id] = task
                            # 如果任务状态为进行中，更新为失败（服务重启后无法继续）
                            if task.get('state') == 'PROGRESS':
                                filtered_tasks[task_id]['state'] = 'FAILED'
                                filtered_tasks[task_id]['error'] = '服务重启，任务中断'
                                if 'logs' in filtered_tasks[task_id]:
                                    filtered_tasks[task_id]['logs'].append({
                                        'timestamp': datetime.now().isoformat(),
                                        'level': 'error',
                                        'message': '服务重启，任务中断'
                                    })
                    except Exception:
                        continue
                
                tasks = filtered_tasks
                valid_tasks = [task for task in tasks.values() if isinstance(task, dict)]
                if valid_tasks:
                    last_update = max([datetime.fromisoformat(task.get('last_activity_time', '1970-01-01T00:00:00.000Z').replace('Z', '+00:00')) for task in valid_tasks], default=datetime.fromtimestamp(0))
                    print(f"任务状态已从文件加载，共 {len(tasks)} 个任务，最后更新时间: {last_update.isoformat()}")
                else:
                    print(f"任务状态已从文件加载，共 {len(tasks)} 个任务")
    except Exception as e:
        logger.exception("加载任务状态失败")
        tasks = {}

# 加载配置文件
def load_config_file():
    """加载配置文件"""
    global config
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 合并默认配置和加载的配置
                config = {**DEFAULT_CONFIG, **loaded_config}
                # 确保user_id_list是列表
                if 'user_id_list' in config and isinstance(config['user_id_list'], str):
                    config['user_id_list'] = [uid.strip() for uid in config['user_id_list'].split(',') if uid.strip()]
                print(f"配置已从文件加载: {CONFIG_FILE_PATH}")
        else:
            # 使用默认配置
            config = DEFAULT_CONFIG.copy()
            # 保存默认配置到文件
            save_config_file()
            print(f"使用默认配置，并保存到文件: {CONFIG_FILE_PATH}")
    except Exception as e:
        logger.exception("加载配置文件失败")
        config = DEFAULT_CONFIG.copy()

# 保存配置文件
def save_config_file():
    """保存配置文件"""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("保存配置文件失败")

# 定时刷新任务
def schedule_refresh():
    """定时执行刷新任务"""
    while True:
        try:
            if schedule_config['enabled']:
                # 检查是否有正在运行的任务
                with task_lock:
                    if not current_task_id:
                        # 创建新任务
                        task_id = str(uuid.uuid4())
                        tasks[task_id] = {
                            'state': 'PENDING',
                            'progress': 0,
                            'created_at': datetime.now().isoformat(),
                            'user_id_list': config.get('user_id_list', [])
                        }
                        current_task_id = task_id
                        save_tasks_state()
                        
                        # 提交任务到线程池
                        executor.submit(run_refresh_task, task_id)
                        logger.info(f"定时任务已启动，任务ID: {task_id}")
            
            # 根据配置的间隔时间等待
            if schedule_config['interval'] == 'hourly':
                time.sleep(60 * 60)
            elif schedule_config['interval'] == 'daily':
                time.sleep(24 * 60 * 60)
            elif schedule_config['interval'] == 'weekly':
                time.sleep(7 * 24 * 60 * 60)
            elif schedule_config['interval'] == 'custom':
                time.sleep(schedule_config['custom_interval'] * 60)
            else:
                time.sleep(60 * 60)  # 默认1小时
        except Exception as e:
            logger.exception("定时任务执行失败")
            time.sleep(60)  # 出错后等待1分钟再试

# API路由

# 获取当前正在运行的任务
@app.route('/task/current', methods=['GET'])
def get_current_task():
    """获取当前正在运行的任务"""
    try:
        with task_lock:
            if current_task_id and current_task_id in tasks:
                task = tasks[current_task_id]
                return jsonify({
                    "task_id": current_task_id,
                    "state": task.get('state', 'UNKNOWN'),
                    "progress": task.get('progress', 0),
                    "start_time": task.get('start_time', None),
                    "last_activity_time": task.get('last_activity_time', None)
                }), 200
            else:
                return jsonify({"task_id": None}), 200
    except Exception as e:
        logger.exception("获取当前任务失败")
        return jsonify({"error": str(e)}), 500

# 获取任务状态
@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    try:
        # 首先尝试从内存获取任务状态
        if task_id in tasks:
            task = tasks[task_id]
            response = {
                "state": task.get('state', 'UNKNOWN'),
                "progress": task.get('progress', 0)
            }
            
            # 如果任务有结果，添加到响应中
            if 'result' in task:
                response['result'] = task['result']
            # 如果任务有错误，添加到响应中
            if 'error' in task:
                response['error'] = task['error']
            # 添加任务的开始时间和最后活动时间
            if 'start_time' in task:
                response['start_time'] = task['start_time']
            # 添加任务日志
            if 'logs' in task:
                response['logs'] = task['logs']
            if 'last_activity_time' in task:
                response['last_activity_time'] = task['last_activity_time']
            
            logger.info(f"获取任务 {task_id} 状态: {response['state']}, 进度: {response['progress']}%")
            return jsonify(response), 200
        else:
            # 如果内存中没有，返回任务不存在
            return jsonify({"error": "任务不存在"}), 404
    except Exception as e:
        logger.exception(f"获取任务 {task_id} 状态失败")
        return jsonify({"error": str(e)}), 500

# 取消任务
@app.route('/task/cancel', methods=['POST'])
def cancel_task():
    """取消当前任务"""
    try:
        with task_lock:
            global current_task_id
            if current_task_id and current_task_id in tasks:
                tasks[current_task_id]['state'] = 'CANCELLED'
                tasks[current_task_id]['progress'] = 0
                tasks[current_task_id]['last_activity_time'] = datetime.now().isoformat()
                tasks[current_task_id]['error'] = '任务已取消'
                if 'logs' in tasks[current_task_id]:
                    tasks[current_task_id]['logs'].append({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'warning',
                        'message': '任务已取消'
                    })
                save_tasks_state()
                logger.info(f"任务 {current_task_id} 已取消")
                # 清除当前任务ID
                current_task_id = None
                return jsonify({"message": "任务已取消"}), 200
            else:
                return jsonify({"error": "没有正在运行的任务"}), 404
    except Exception as e:
        logger.exception("取消任务失败")
        return jsonify({"error": str(e)}), 500

# 获取所有任务
@app.route('/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务"""
    try:
        with task_lock:
            return jsonify(tasks), 200
    except Exception as e:
        logger.exception("获取所有任务失败")
        return jsonify({"error": str(e)}), 500

# 刷新任务
@app.route('/refresh', methods=['POST'])
def refresh():
    """启动刷新任务"""
    try:
        # 获取请求数据
        data = request.get_json() or {}
        
        # 创建新任务
        task_id = str(uuid.uuid4())
        
        # 从请求中获取user_id_list，如果没有则使用全局配置
        user_id_list = data.get('user_id_list')
        
        # 创建任务
        with task_lock:
            tasks[task_id] = {
                'state': 'PENDING',
                'progress': 0,
                'created_at': datetime.now().isoformat(),
                'user_id_list': user_id_list if user_id_list else config.get('user_id_list', []),
                'logs': [{
                    'timestamp': datetime.now().isoformat(),
                    'level': 'info',
                    'message': f"任务已创建，用户列表: {user_id_list if user_id_list else config.get('user_id_list', [])}"
                }]
            }
            
            # 设置为当前任务
            global current_task_id
            current_task_id = task_id
            
            # 保存任务状态
            save_tasks_state()
        
        # 提交任务到线程池
        executor.submit(run_refresh_task, task_id, user_id_list)
        
        # 返回任务ID
        return jsonify({
            'task_id': task_id,
            'message': '任务已启动'
        }), 200
    except Exception as e:
        logger.exception("启动任务失败")
        return jsonify({"error": str(e)}), 500

# 保存配置
@app.route('/config', methods=['POST'])
def save_config_api():
    """保存配置"""
    try:
        global config
        config_data = request.get_json()
        
        # 更新配置
        config = {**DEFAULT_CONFIG, **config_data}
        
        # 确保user_id_list是列表
        if 'user_id_list' in config and isinstance(config['user_id_list'], str):
            config['user_id_list'] = [uid.strip() for uid in config['user_id_list'].split(',') if uid.strip()]
        
        # 保存配置到文件
        save_config_file()
        
        return jsonify({"message": "配置已保存"}), 200
    except Exception as e:
        logger.exception("保存配置失败")
        return jsonify({"error": str(e)}), 500

# 获取配置
@app.route('/config', methods=['GET'])
def get_config_api():
    """获取配置"""
    try:
        if not config:
            load_config_file()
        return jsonify(config), 200
    except Exception as e:
        logger.exception("获取配置失败")
        return jsonify({"error": str(e)}), 500

# 重新加载配置
@app.route('/config/reload', methods=['POST'])
def reload_config():
    """重新加载配置"""
    try:
        load_config_file()
        return jsonify({"message": "配置已重新加载"}), 200
    except Exception as e:
        logger.exception("重新加载配置失败")
        return jsonify({"error": str(e)}), 500

# 首页路由
@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

# 获取结果列表
@app.route('/results', methods=['GET'])
def get_results():
    """获取结果列表"""
    try:
        results = []
        weibo_dir = os.path.join(BASE_DIR, 'weibo')
        
        # 遍历weibo目录下的所有文件夹
        for uid in os.listdir(weibo_dir):
            uid_path = os.path.join(weibo_dir, uid)
            if os.path.isdir(uid_path):
                # 统计文件数量
                file_count = 0
                image_count = 0
                csv_files = []
                db_files = []
                
                # 遍历用户文件夹下的所有文件
                for file in os.listdir(uid_path):
                    file_path = os.path.join(uid_path, file)
                    if os.path.isfile(file_path):
                        file_count += 1
                        # 检查文件类型
                        if file.endswith('.csv'):
                            csv_files.append(file)
                        elif file.endswith('.db'):
                            db_files.append(file)
                        # 检查是否为图片文件
                        elif file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                            image_count += 1
                
                # 获取文件夹的最后修改时间
                last_update = datetime.fromtimestamp(os.path.getmtime(uid_path)).strftime('%Y-%m-%d %H:%M')
                
                # 添加用户数据到结果列表
                results.append({
                    'id': uid,
                    'name': f'用户_{uid}',  # 这里可以根据实际情况从数据库或其他地方获取真实用户名
                    'weiboCount': 0,  # 这里可以根据实际情况从数据库或文件中获取微博数量
                    'fileCount': file_count,
                    'imageCount': image_count,
                    'lastUpdate': last_update,
                    'files': [
                        {'name': f'{uid}_data.csv', 'type': 'csv', 'size': '0 MB'} if csv_files else {},
                        {'name': f'{uid}_data.db', 'type': 'db', 'size': '0 MB'} if db_files else {}
                    ]
                })
        
        return jsonify(results), 200
    except Exception as e:
        logger.exception("获取结果列表失败")
        return jsonify({"error": str(e)}), 500

# 微博登录路由
@app.route('/weibo/login', methods=['POST'])
def weibo_login():
    """微博登录获取Cookie"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        # 获取请求数据
        login_data = request.get_json()
        username = login_data.get('username')
        password = login_data.get('password')
        
        if not username or not password:
            return jsonify({'error': '请提供用户名和密码'}), 400
        
        # 创建会话
        session = requests.Session()
        
        # 1. 访问登录页面获取登录所需参数
        login_url = 'https://passport.weibo.cn/signin/login'
        response = session.get(login_url)
        
        # 解析页面获取vk和其他参数
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找vk值
        vk_input = soup.find('input', {'name': 'vk'})
        if not vk_input:
            return jsonify({'error': '无法获取登录参数vk'}), 500
        vk = vk_input.get('value')
        
        # 查找from值
        from_input = soup.find('input', {'name': 'from'})
        from_value = from_input.get('value') if from_input else ''
        
        # 2. 发送登录请求
        login_post_url = 'https://passport.weibo.cn/sso/login'
        login_payload = {
            'username': username,
            'password': password,
            'savestate': '1',
            'r': 'https://m.weibo.cn/',
            'ec': '0',
            'pagerefer': 'https://m.weibo.cn/login?backURL=https%253A%252F%252Fm.weibo.cn%252F',
            'entry': 'mweibo',
            'wentry': '',
            'loginfrom': '',
            'client_id': '',
            'code': '',
            'qq': '',
            'mainpageflag': '1',
            'hff': '',
            'hfp': '',
            'vk': vk,
            'from': from_value
        }
        
        login_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://passport.weibo.cn/signin/login',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        login_response = session.post(login_post_url, data=login_payload, headers=login_headers)
        login_result = login_response.json()
        
        if login_result.get('retcode') != 20000000:
            return jsonify({'error': f'登录失败: {login_result.get("msg", "未知错误")}'}), 401
        
        # 3. 访问微博.cn获取完整Cookie
        cn_response = session.get('https://weibo.cn')
        
        # 4. 提取Cookie
        cookie_dict = session.cookies.get_dict()
        cookie_str = '; '.join([f'{k}={v}' for k, v in cookie_dict.items()])
        
        if not cookie_str:
            return jsonify({'error': '无法获取Cookie'}), 500
        
        # 5. 保存Cookie到配置
        global config
        config['cookie'] = cookie_str
        save_config_file()
        
        return jsonify({'cookie': cookie_str, 'message': '登录成功'}), 200
        
    except Exception as e:
        logger.exception(f"微博登录失败: {e}")
        return jsonify({'error': f'登录失败: {str(e)}'}), 500

# 静态文件路由
@app.route('/static/<path:path>')
def send_static(path):
    """发送静态文件"""
    return send_from_directory(app.static_folder, path)

# 直接运行时启动服务
if __name__ == '__main__':
    # 加载配置
    load_config_file()
    
    # 加载任务状态
    load_tasks_state()
    
    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=schedule_refresh, daemon=True)
    scheduler_thread.start()
    
    # 启动服务
    logger.info("服务启动 (直接运行模式)")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)  # 关闭reloader避免重复启动
