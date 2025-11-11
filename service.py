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

# 1896820725 天津股侠 2024-12-09T16:47:04

DATABASE_PATH = './weibo/weibodata.db'
print(DATABASE_PATH)

# 如果日志文件夹不存在，则创建
if not os.path.isdir("log/"):
    os.makedirs("log/")
logging_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + "logging.conf"
logging.config.fileConfig(logging_path)
logger = logging.getLogger("api")

config = {
    "user_id_list": [
        "6067225218", 
        "1445403190"
        ],
    "query_list": "",
    "only_crawl_original": 1,
    "since_date": 1,
    "start_page": 1,
    "write_mode": [
        "csv",
        "json",
        "sqlite"
    ],
    "original_pic_download": 0,
    "retweet_pic_download": 0,
    "original_video_download": 0,
    "retweet_video_download": 0,
    "download_comment": 0,
    "comment_max_download_count": 100,
    "download_repost": 0,
    "repost_max_download_count": 100,
    "user_id_as_folder_name": 0,
    "remove_html_tag": 1,
    "cookie": "your weibo cookie",
    "mysql_config": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "123456",
        "charset": "utf8mb4"
    },
    "mongodb_URI": "mongodb://[username:password@]host[:port][/[defaultauthdb][?options]]",
    "post_config": {
        "api_url": "https://api.example.com",
        "api_token": ""
    }
}

# 创建Flask应用实例
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # 添加CORS支持，允许所有来源的跨域请求

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置静态文件目录
app.static_folder = os.path.join(BASE_DIR, 'static')
app.template_folder = BASE_DIR
app.config['JSON_AS_ASCII'] = False  # 确保JSON响应中的中文不会被转义
app.config['JSONIFY_MIMETYPE'] = 'application/json;charset=utf-8'

# 添加线程池和任务状态跟踪
executor = ThreadPoolExecutor(max_workers=1)  # 限制只有1个worker避免并发爬取
tasks = {}

# 在executor定义后添加任务锁相关变量
current_task_id = None
task_lock = threading.Lock()

# 任务管理
tasks = {}
tasks_lock = threading.Lock()

# 定期爬取配置
schedule_config = {
    "enabled": False,
    "interval": "daily",  # options: hourly, daily, weekly, custom
    "custom_interval": 60  # in minutes, used when interval is "custom"
}

# 配置文件路径
CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.json')

def get_running_task():
    """获取当前运行的任务信息，添加超时检测"""
    if current_task_id and current_task_id in tasks:
        task = tasks[current_task_id]
        if task['state'] in ['PENDING', 'PROGRESS']:
            # 检查任务是否超时（30分钟）
            created_at = datetime.fromisoformat(task['created_at'])
            if (datetime.now() - created_at).total_seconds() > 30 * 60:
                logger.warning(f"任务 {current_task_id} 已超过30分钟未完成，标记为超时")
                task['state'] = 'TIMEOUT'
                return None, None
            return current_task_id, task
    return None, None

def get_config(user_id_list=None):
    """获取配置，允许动态设置user_id_list"""
    current_config = config.copy()
    if user_id_list:
        current_config['user_id_list'] = user_id_list
    
    # 完全避免使用handle_config_renaming函数，直接手动处理参数映射
    # 这样可以避免任何可能的KeyError异常
    if "filter" in current_config and "only_crawl_original" not in current_config:
        current_config["only_crawl_original"] = current_config["filter"]
        del current_config["filter"]
    
    if "result_dir_name" in current_config and "user_id_as_folder_name" not in current_config:
        current_config["user_id_as_folder_name"] = current_config["result_dir_name"]
        del current_config["result_dir_name"]
    
    # 确保没有'original_live_photo_download'参数，避免后续错误
    if "original_live_photo_download" in current_config:
        del current_config["original_live_photo_download"]
    
    logger.info("配置加载完成，参数映射处理完毕")
    return current_config

def run_refresh_task(task_id, user_id_list=None):
    global current_task_id
    timeout = 30 * 60  # 30分钟超时
    start_time = time.time()
    
    try:
        tasks[task_id]['state'] = 'PROGRESS'
        tasks[task_id]['progress'] = 0
        
        # 确保weibo目录存在
        weibo_dir = os.path.join(BASE_DIR, 'weibo')
        if not os.path.exists(weibo_dir):
            os.makedirs(weibo_dir)
            logger.info(f"Created weibo directory: {weibo_dir}")
        
        config = get_config(user_id_list)
        # 确保图片下载配置正确传递
        logger.info(f"Task config: {json.dumps(config, ensure_ascii=False)}")
        
        # 初始化进度更新定时器 - 更频繁地更新进度
        def update_progress():
            if tasks[task_id]['state'] == 'PROGRESS' and time.time() - start_time < timeout:
                # 根据运行时间更新进度
                elapsed = time.time() - start_time
                # 线性增长，但不超过90%
                new_progress = min(90, int((elapsed / timeout) * 90))
                if new_progress > tasks[task_id]['progress']:
                    tasks[task_id]['progress'] = new_progress
                    logger.info(f"Task {task_id}: 进度更新为 {new_progress}%")
                # 每10秒更新一次进度，更频繁
                threading.Timer(10, update_progress).start()
        
        # 启动进度更新
        update_progress()
        
        # 模拟进度更新的中间步骤，更平滑的进度
        tasks[task_id]['progress'] = 15
        logger.info(f"Task {task_id}: 初始化完成")
        time.sleep(0.5)  # 给前端时间显示更新
        
        tasks[task_id]['progress'] = 25
        logger.info(f"Task {task_id}: 配置加载完成")
        time.sleep(0.5)
        
        wb = Weibo(config)
        tasks[task_id]['progress'] = 35
        logger.info(f"Task {task_id}: 微博实例创建完成")
        time.sleep(0.5)
        
        tasks[task_id]['progress'] = 45
        logger.info(f"Task {task_id}: 准备开始爬取")
        time.sleep(0.5)
        
        # 设置超时的start方法调用
        result_event = threading.Event()
        error_info = [None]
        
        # 增加一个进度更新的线程，定期更新进度
        progress_update_active = [True]
        
        def progress_monitor():
            while progress_update_active[0] and tasks[task_id]['state'] == 'PROGRESS':
                # 每5秒更新一次进度，确保用户看到活动
                time.sleep(5)
                if tasks[task_id]['state'] == 'PROGRESS':
                    # 逐步增加进度，避免卡在某一值
                    current_progress = tasks[task_id]['progress']
                    if current_progress < 85:
                        new_progress = min(current_progress + 3, 85)
                        tasks[task_id]['progress'] = new_progress
                        logger.info(f"Task {task_id}: 爬取进行中，进度 {new_progress}%")
        
        # 启动进度监控线程
        monitor_thread = threading.Thread(target=progress_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 增加额外的进度更新点，确保进度不会卡在25%
        def additional_progress_updater():
            for p in [30, 35, 40, 45, 50]:
                time.sleep(2)  # 每2秒更新一次进度
                if tasks[task_id]['state'] == 'PROGRESS' and tasks[task_id]['progress'] < p:
                    tasks[task_id]['progress'] = p
                    logger.info(f"Task {task_id}: 进度更新为 {p}%")
        
        # 启动额外的进度更新线程
        progress_thread = threading.Thread(target=additional_progress_updater)
        progress_thread.daemon = True
        progress_thread.start()
        
        def start_weibo():
            try:
                wb.start()  # 爬取微博信息
                progress_update_active[0] = False
                result_event.set()
            except Exception as e:
                error_info[0] = e
                progress_update_active[0] = False
                result_event.set()
        
        # 在单独线程中运行爬取
        thread = threading.Thread(target=start_weibo)
        thread.daemon = True
        thread.start()
        
        # 等待完成或超时
        if not result_event.wait(timeout=timeout):
            progress_update_active[0] = False
            logger.error(f"Task {task_id} 执行超时（超过30分钟）")
            tasks[task_id]['state'] = 'FAILED'
            tasks[task_id]['error'] = "任务执行超时（超过30分钟）"
            return
        
        # 检查是否有错误
        if error_info[0]:
            progress_update_active[0] = False
            logger.error(f"Task {task_id} 执行出错: {error_info[0]}")
            tasks[task_id]['state'] = 'FAILED'
            tasks[task_id]['error'] = str(error_info[0])
            return
        
        # 记录爬取结果信息
        logger.info(f"Task {task_id} completed successfully")
        tasks[task_id]['progress'] = 100
        tasks[task_id]['state'] = 'SUCCESS'
        tasks[task_id]['result'] = {"message": "微博列表已刷新"}
        
    except TimeoutError as te:
        logger.error(f"Task {task_id} timeout: {te}")
        tasks[task_id]['state'] = 'FAILED'
        tasks[task_id]['error'] = str(te)
    except Exception as e:
        logger.exception(f"Error in task {task_id}: {e}")
        tasks[task_id]['state'] = 'FAILED'
        tasks[task_id]['error'] = str(e)
    finally:
        with task_lock:
            if current_task_id == task_id:
                current_task_id = None

@app.route('/refresh', methods=['POST'])
def refresh():
    global current_task_id
    
    # 获取请求参数
    data = request.get_json() or {}
    
    # 使用请求中的user_id_list，如果没有则使用配置中的默认值
    user_id_list = data.get('user_id_list')
    
    # 验证参数，如果无效则使用配置中的默认值
    if not user_id_list or not isinstance(user_id_list, list) or len(user_id_list) == 0:
        user_id_list = config.get('user_id_list', [])
        logger.info(f'未提供有效的user_id_list，使用默认配置: {user_id_list}')
    
    # 字符串转列表的类型转换逻辑
    if isinstance(user_id_list, str):
        logger.info(f'将字符串类型的user_id_list转换为列表: {user_id_list}')
        # 处理以逗号分隔的多个ID，或单个ID
        user_id_list = [uid.strip() for uid in user_id_list.split(',') if uid.strip()]
    
    # 确保user_id_list是有效的列表类型
    if not isinstance(user_id_list, list):
        logger.error(f'Invalid user_id_list parameter format: {type(user_id_list)}')
        return jsonify({
            'error': '无效的user_id_list参数格式'
        }), 400
    
    logger.info(f'准备执行任务，使用user_id_list: {user_id_list}')
    
    # 检查是否有正在运行的任务，添加强制覆盖选项
    force = data.get('force', False)
    
    with task_lock:
        running_task_id, running_task = get_running_task()
        if running_task and not force:
            return jsonify({
                'task_id': running_task_id,
                'status': 'Task already running',
                'state': running_task['state'],
                'progress': running_task['progress'],
                'hint': '可以通过添加 {"force": true} 参数强制创建新任务'
            }), 409  # 409 Conflict
        
        # 如果有运行中的任务且强制创建，记录日志
        if running_task and force:
            logger.warning(f"强制创建新任务，中断正在运行的任务 {running_task_id}")
            running_task['state'] = 'INTERRUPTED'
        
        # 创建新任务
        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            'state': 'PENDING',
            'progress': 0,
            'created_at': datetime.now().isoformat(),
            'user_id_list': user_id_list
        }
        current_task_id = task_id
        
    executor.submit(run_refresh_task, task_id, user_id_list)
    return jsonify({
        'task_id': task_id,
        'status': 'Task started',
        'state': 'PENDING',
        'progress': 0,
        'user_id_list': user_id_list
    }), 202

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
        
    response = {
        'state': task['state'],
        'progress': task['progress']
    }
    
    if task['state'] == 'SUCCESS':
        response['result'] = task.get('result')
    elif task['state'] == 'FAILED':
        response['error'] = task.get('error')
        
    return jsonify(response)

@app.route('/task/cancel', methods=['POST'])
def cancel_task():
    global current_task_id
    with task_lock:
        if current_task_id and current_task_id in tasks:
            # 在实际应用中，这里可能需要更复杂的停止机制
            # 由于我们使用ThreadPoolExecutor，这里只是标记任务为停止状态
            tasks[current_task_id]['state'] = 'STOPPED'
            tasks[current_task_id]['result'] = {"message": "任务已手动停止"}
            current_task_id = None
            return jsonify({"message": "任务已停止"})
        else:
            return jsonify({"error": "没有正在运行的任务"}), 404

@app.route('/weibos', methods=['GET'])
def get_weibos():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        # 按created_at倒序查询所有微博
        cursor.execute("SELECT * FROM weibo ORDER BY created_at DESC")
        columns = [column[0] for column in cursor.description]
        weibos = []
        for row in cursor.fetchall():
            weibo = dict(zip(columns, row))
            weibos.append(weibo)
        conn.close()
        res1 = json.dumps(weibos, ensure_ascii=False)
        print(res1)
        res = jsonify(weibos)
        print(res)
        return res, 200
    except Exception as e:
        logger.exception(e)
        return {"error": str(e)}, 500

@app.route('/weibos/<weibo_id>', methods=['GET'])
def get_weibo_detail(weibo_id):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weibo WHERE id=?", (weibo_id,))
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        conn.close()
        
        if row:
            weibo = dict(zip(columns, row))
            return jsonify(weibo), 200
        else:
            return {"error": "Weibo not found"}, 404
    except Exception as e:
        logger.exception(e)
        return {"error": str(e)}, 500

@app.route('/config/schedule', methods=['GET', 'PUT'])
def handle_schedule_config():
    """处理定期爬取配置"""
    global schedule_config
    
    if request.method == 'GET':
        # 返回当前配置
        return jsonify(schedule_config), 200
    
    elif request.method == 'PUT':
        # 更新配置
        try:
            data = request.get_json()
            if data:
                # 验证并更新配置
                if 'enabled' in data:
                    schedule_config['enabled'] = bool(data['enabled'])
                if 'interval' in data and data['interval'] in ['hourly', 'daily', 'weekly', 'custom']:
                    schedule_config['interval'] = data['interval']
                if 'custom_interval' in data:
                    # 确保自定义间隔是正整数
                    custom_interval = int(data['custom_interval'])
                    if custom_interval > 0:
                        schedule_config['custom_interval'] = custom_interval
                
                # 将配置保存到文件
                save_config_file()
                
                return jsonify({"success": True, "message": "Schedule config updated", "config": schedule_config}), 200
            else:
                return {"error": "No data provided"}, 400
        except Exception as e:
            logger.exception("Error updating schedule config")
            return {"error": str(e)}, 500

@app.route('/config/base', methods=['GET', 'PUT'])
def handle_base_config():
    """处理基础配置"""
    global config
    
    if request.method == 'GET':
        # 返回当前基础配置
        logger.info("获取基础配置请求")
        return jsonify({
            "user_id_list": config.get('user_id_list', []),
            "query_list": config.get('query_list', ''),
            "only_crawl_original": config.get('only_crawl_original', 1),
            "since_date": config.get('since_date', 1),
            "write_mode": config.get('write_mode', ['csv', 'sqlite']),
            "original_pic_download": config.get('original_pic_download', 0),
            "retweet_pic_download": config.get('retweet_pic_download', 0),
            "original_video_download": config.get('original_video_download', 0),
            "retweet_video_download": config.get('retweet_video_download', 0),
            "cookie": config.get('cookie', '')
        }), 200
    
    elif request.method == 'PUT':
        # 更新基础配置
        try:
            data = request.get_json() or {}
            logger.info(f"更新基础配置请求，接收到的数据: {data}")
            
            # 基础配置项列表
            base_config_keys = [
                'user_id_list', 'query_list', 'only_crawl_original', 'since_date',
                'original_pic_download', 'retweet_pic_download',
                'original_video_download', 'retweet_video_download', 'cookie'
            ]
            
            # 更新各项配置
            for key in base_config_keys:
                if key in data:
                    # 特殊处理user_id_list，确保格式正确
                    if key == 'user_id_list':
                        logger.info(f"更新user_id_list: {data[key]}")
                    config[key] = data[key]
            
            # 确保write_mode是数组格式
            if 'write_mode' in data:
                if isinstance(data['write_mode'], list):
                    config['write_mode'] = data['write_mode']
                else:
                    config['write_mode'] = [data['write_mode']]
            
            # 将配置保存到文件
            try:
                save_config_file()
                logger.info("基础配置保存成功")
                return jsonify({"success": True, "message": "基础配置更新成功并已保存到文件", "config": config}), 200
            except Exception as save_error:
                logger.error(f"保存配置文件失败: {str(save_error)}")
                return jsonify({"success": False, "error": f"配置已更新但保存失败: {str(save_error)}"}), 500
                
        except ValueError as ve:
            logger.error(f"配置值错误: {str(ve)}")
            return jsonify({"success": False, "error": f"配置值格式错误: {str(ve)}"}), 400
        except Exception as e:
            logger.exception(f"更新基础配置时发生错误: {str(e)}")
            return jsonify({"success": False, "error": f"更新配置失败: {str(e)}"}), 500

@app.route('/config/database', methods=['GET', 'PUT'])
def handle_database_config():
    """处理数据库配置"""
    global config
    
    if request.method == 'GET':
        return jsonify({
            "mysql_config": config.get('mysql_config', {}),
            "mongodb_URI": config.get('mongodb_URI', '')
        }), 200
    
    elif request.method == 'PUT':
        try:
            data = request.get_json() or {}
            
            # 根据前端选择的数据库类型更新配置
            if 'mysql_config' in data:
                # 确保mysql_config是字典类型
                if isinstance(data['mysql_config'], dict):
                    # 更新mysql配置，保留未提供的字段
                    current_mysql_config = config.get('mysql_config', {})
                    current_mysql_config.update(data['mysql_config'])
                    config['mysql_config'] = current_mysql_config
            
            if 'mongodb_URI' in data:
                config['mongodb_URI'] = data['mongodb_URI']
            
            # 保存配置到文件
            save_config_file()
            return jsonify({"success": True, "message": "数据库配置更新成功"}), 200
        except Exception as e:
            logger.error(f"更新数据库配置失败: {e}")
            # 提供更详细的错误信息
            return jsonify({"success": False, "error": f"更新配置失败: {str(e)}"}), 500

def save_config_file():
    """保存配置到文件"""
    try:
        # 读取现有配置
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
        else:
            current_config = {}
        
        # 更新配置
        # 基础配置项
        # 处理user_id_list类型转换，确保是列表格式
        user_id_list = config.get('user_id_list', [])
        if isinstance(user_id_list, str):
            # 如果是字符串，按逗号分割并去空
            current_config['user_id_list'] = [id.strip() for id in user_id_list.split(',') if id.strip()]
        else:
            current_config['user_id_list'] = user_id_list
        
        current_config['query_list'] = config.get('query_list', '')
        current_config['only_crawl_original'] = config.get('only_crawl_original', 1)
        current_config['since_date'] = config.get('since_date', 1)
        current_config['start_page'] = config.get('start_page', 1)
        current_config['write_mode'] = config.get('write_mode', ['csv', 'sqlite'])  # 默认包含sqlite
        current_config['original_pic_download'] = config.get('original_pic_download', 0)
        current_config['retweet_pic_download'] = config.get('retweet_pic_download', 0)
        current_config['original_video_download'] = config.get('original_video_download', 0)
        current_config['retweet_video_download'] = config.get('retweet_video_download', 0)
        current_config['download_comment'] = config.get('download_comment', 0)
        current_config['comment_max_download_count'] = config.get('comment_max_download_count', 100)
        current_config['download_repost'] = config.get('download_repost', 0)
        current_config['repost_max_download_count'] = config.get('repost_max_download_count', 100)
        current_config['user_id_as_folder_name'] = config.get('user_id_as_folder_name', 0)
        current_config['remove_html_tag'] = config.get('remove_html_tag', 1)
        current_config['cookie'] = config.get('cookie', '')
        
        # 数据库配置 - 只有在前端发送了对应配置时才保存
        # 这样可以确保只有勾选了对应数据库的启用复选框时，才会更新该数据库配置
        if 'mysql_config' in config:
            current_config['mysql_config'] = config['mysql_config']
        if 'mongodb_URI' in config:
            current_config['mongodb_URI'] = config['mongodb_URI']
        
        # 定期爬取配置
        current_config['schedule_config'] = schedule_config
        
        # 添加配置保存前的检查
        logger.info(f"准备保存配置到文件: {CONFIG_FILE_PATH}")
        
        # 确保目录存在
        config_dir = os.path.dirname(CONFIG_FILE_PATH)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
            logger.info(f"创建配置目录: {config_dir}")
        
        # 保存配置
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=2)
        
        # 验证保存是否成功
        if os.path.exists(CONFIG_FILE_PATH):
            logger.info(f"配置文件保存成功，文件大小: {os.path.getsize(CONFIG_FILE_PATH)} 字节")
            # 读取保存后的文件进行验证
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                logger.info(f"保存的配置包含user_id_list: {saved_config.get('user_id_list')}")
        else:
            logger.error(f"配置文件保存失败，文件不存在: {CONFIG_FILE_PATH}")
            
    except PermissionError:
        logger.error(f"没有权限写入配置文件: {CONFIG_FILE_PATH}，请检查文件权限")
    except json.JSONDecodeError:
        logger.error(f"配置文件格式错误，无法解析: {CONFIG_FILE_PATH}")
    except Exception as e:
        logger.exception(f"保存配置文件时发生错误: {str(e)}")
        raise  # 重新抛出异常，让调用者知道保存失败

def schedule_refresh():
    """定时刷新任务"""
    while True:
        try:
            # 检查是否启用了定期爬取
            if schedule_config.get("enabled", False):
                # 检查是否有运行中的任务
                running_task_id, running_task = get_running_task()
                if not running_task:
                    task_id = str(uuid.uuid4())
                    tasks[task_id] = {
                        'state': 'PENDING',
                        'progress': 0,
                        'created_at': datetime.now().isoformat(),
                        'user_id_list': config['user_id_list']  # 使用默认配置
                    }
                    with task_lock:
                        global current_task_id
                        current_task_id = task_id
                    executor.submit(run_refresh_task, task_id, config['user_id_list'])
                    logger.info(f"Scheduled task {task_id} started")
            
            # 根据配置的间隔时间等待
            interval = schedule_config.get("interval", "daily")
            if interval == "hourly":
                wait_time = 3600  # 1小时
            elif interval == "daily":
                wait_time = 86400  # 24小时
            elif interval == "weekly":
                wait_time = 604800  # 7天
            elif interval == "custom":
                wait_time = int(schedule_config.get("custom_interval", 60)) * 60  # 自定义分钟数转换为秒
            else:
                wait_time = 86400  # 默认24小时
                
            # 每60秒检查一次配置是否变化
            for _ in range(int(wait_time / 60)):
                time.sleep(60)
                # 重新加载配置（如果有变化）
                load_config_file()
                
        except Exception as e:
            logger.exception("Schedule task error")
            time.sleep(60)  # 发生错误时等待1分钟后重试

def load_config_file():
    """从配置文件加载配置"""
    global config, schedule_config
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
                # 更新基础配置项
                base_config_keys = [
                    'user_id_list', 'query_list', 'only_crawl_original', 'since_date',
                    'start_page', 'write_mode', 'original_pic_download', 'retweet_pic_download',
                    'original_video_download', 'retweet_video_download', 'download_comment',
                    'comment_max_download_count', 'download_repost', 'repost_max_download_count',
                    'user_id_as_folder_name', 'remove_html_tag', 'cookie'
                ]
                for key in base_config_keys:
                    if key in new_config:
                        config[key] = new_config[key]
                
                # 更新数据库配置
                if 'mysql_config' in new_config:
                    config['mysql_config'] = new_config['mysql_config']
                if 'mongodb_URI' in new_config:
                    config['mongodb_URI'] = new_config['mongodb_URI']
                
                # 更新定期爬取配置
                if 'schedule_config' in new_config:
                    schedule_config.update(new_config['schedule_config'])
    except Exception as e:
        logger.exception("Error loading config file")

@app.route('/')
def index():
    """首页路由"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件路由"""
    return send_from_directory(app.static_folder, filename)

if __name__ == "__main__":
    # 加载配置文件
    load_config_file()
    
    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=schedule_refresh, daemon=True)
    scheduler_thread.start()
    
    logger.info("服务启动")
    # 启动Flask应用
    app.run(debug=True, use_reloader=False)  # 关闭reloader避免启动两次