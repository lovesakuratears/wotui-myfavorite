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

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 使用绝对路径确保数据库路径的正确性
DATABASE_PATH = os.path.join(BASE_DIR, 'weibo', 'weibodata.db')
print(f"数据库路径: {DATABASE_PATH}")

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

# 任务状态持久化文件路径
TASKS_FILE_PATH = os.path.join(BASE_DIR, 'tasks_state.json')

# 定期爬取配置
schedule_config = {
    "enabled": False,
    "interval": "daily",  # options: hourly, daily, weekly, custom
    "custom_interval": 60  # in minutes, used when interval is "custom"
}

# 配置文件路径
CONFIG_FILE_PATH = os.path.join(BASE_DIR, 'config.json')

def get_running_task():
    """获取当前正在运行的任务"""
    global current_task_id, tasks
    with task_lock:
        if current_task_id and current_task_id in tasks:
            task = tasks[current_task_id]
            if task.get('state') == 'PROGRESS':
                logger.info(f"当前有运行中的任务: {current_task_id}, 状态: {task.get('state')}, 进度: {task.get('progress')}%")
                return current_task_id, task
    # 遍历所有任务，查找处于PROGRESS状态的任务
    for task_id, task in tasks.items():
        if task.get('state') == 'PROGRESS':
            # 更新current_task_id为找到的运行中任务
            with task_lock:
                current_task_id = task_id
            logger.info(f"找到运行中的任务: {task_id}, 状态: {task.get('state')}, 进度: {task.get('progress')}%")
            return task_id, task
    logger.info("没有找到运行中的任务")
    return None, None

def get_config(user_id_list=None):
    """获取配置，优先使用用户传入的配置，否则使用全局配置
    
    Args:
        user_id_list: 可选，用户ID列表，如果不提供则使用全局配置
    
    Returns:
        配置字典
    """
    # 先尝试从文件加载最新配置
    try:
        load_config_file()
    except Exception as e:
        logger.error(f"加载配置文件时出错: {e}")
    
    # 使用全局配置作为基础
    config_copy = config.copy()
    
    # 如果提供了user_id_list，则覆盖全局配置中的用户ID列表
    if user_id_list:
        logger.info(f"使用自定义用户ID列表: {user_id_list}")
        config_copy["user_id_list"] = user_id_list
    
    return config_copy

def run_refresh_task(task_id, user_id_list=None):
    """运行刷新任务
    
    Args:
        task_id: 任务ID
        user_id_list: 可选，用户ID列表，如果不提供则使用全局配置
    """
    # 获取配置，优先使用用户传入的配置，否则使用全局配置
    task_config = get_config(user_id_list)
    
    # 更新任务状态为进行中
    with task_lock:
        if task_id in tasks:
            tasks[task_id]['state'] = 'PROGRESS'
            tasks[task_id]['progress'] = 0
            tasks[task_id]['start_time'] = datetime.now().isoformat()
            # 保存初始任务状态
            save_tasks_state()
    
    logger.info(f"开始执行刷新任务 {task_id}，用户列表: {task_config.get('user_id_list')}")
    
    # 创建进度更新线程
    stop_event = threading.Event()
    def update_progress():
        
        # 进度更新循环
        while not stop_event.is_set():
            try:
                # 每1秒更新一次任务进度到文件，增加保存频率
                if task_id in tasks:
                    with task_lock:
                        # 确保任务状态正确更新
                        current_time = datetime.now().isoformat()
                        if 'start_time' not in tasks[task_id]:
                            tasks[task_id]['start_time'] = current_time
                        # 更新最后活动时间
                        tasks[task_id]['last_activity_time'] = current_time
                save_tasks_state()
                time.sleep(1)
            except Exception as e:
                logger.error(f"更新任务进度时出错: {e}")
                time.sleep(1)
    
    progress_thread = threading.Thread(target=update_progress, daemon=True)
    progress_thread.start()
    
    # 任务结果
    result = {}
    
    try:
        # 处理配置重命名
        task_config = handle_config_renaming(task_config)
        
        # 创建微博对象
        wb = Weibo(task_config)
        
        # 设置任务超时时间（例如2小时）
        timeout = 2 * 60 * 60  # 2小时
        start_time = time.time()
        
        # 执行爬取任务
        wb.run()
        
        # 更新任务状态为完成
        with task_lock:
            if task_id in tasks:
                tasks[task_id]['state'] = 'COMPLETED'
                tasks[task_id]['progress'] = 100
                tasks[task_id]['end_time'] = datetime.now().isoformat()
                tasks[task_id]['result'] = {"message": "爬取任务完成"}
                save_tasks_state()  # 确保最终状态被保存
    
        logger.info(f"任务 {task_id} 完成")
    
    except Exception as e:
        logger.exception(f"任务 {task_id} 执行失败: {e}")
        # 更新任务状态为失败
        with task_lock:
            if task_id in tasks:
                tasks[task_id]['state'] = 'FAILED'
                tasks[task_id]['result'] = {"error": str(e)}
                tasks[task_id]['end_time'] = datetime.now().isoformat()
                save_tasks_state()  # 确保错误状态被保存
    
    finally:
        # 停止进度更新线程
        stop_event.set()
        progress_thread.join(timeout=5)  # 等待进度更新线程结束
        
        # 确保最终状态被保存
        save_tasks_state()
        # 强制再次保存，确保数据写入
        time.sleep(0.1)
        save_tasks_state()
        
        # 如果当前任务是全局当前任务，则清除
        with task_lock:
            global current_task_id
            if current_task_id == task_id:
                current_task_id = None

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
                'user_id_list': user_id_list if user_id_list else config.get('user_id_list', [])
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
            if 'last_activity_time' in task:
                response['last_activity_time'] = task['last_activity_time']
            
            logger.info(f"获取任务 {task_id} 状态: {response['state']}, 进度: {response['progress']}%")
            return jsonify(response), 200
        else:
            # 尝试重新加载任务状态，看是否能找到该任务
            logger.info(f"尝试从文件加载任务 {task_id} 的状态")
            load_tasks_state()
            if task_id in tasks:
                # 如果重新加载后找到任务，再次获取状态
                task = tasks[task_id]
                response = {
                    "state": task.get('state', 'UNKNOWN'),
                    "progress": task.get('progress', 0)
                }
                if 'result' in task:
                    response['result'] = task['result']
                if 'error' in task:
                    response['error'] = task['error']
                if 'start_time' in task:
                    response['start_time'] = task['start_time']
                if 'last_activity_time' in task:
                    response['last_activity_time'] = task['last_activity_time']
                logger.info(f"重新加载后找到任务 {task_id}, 状态: {response['state']}")
                return jsonify(response), 200
            logger.warning(f"任务 {task_id} 不存在")
            return jsonify({"state": "UNKNOWN", "progress": 0, "error": "任务不存在"}), 404
    except Exception as e:
        logger.exception(f"获取任务状态时出错: {e}")
        return jsonify({"state": "UNKNOWN", "progress": 0, "error": f"获取状态失败: {str(e)}"}), 500

@app.route('/config/reload', methods=['POST'])
def reload_config():
    """重新加载配置文件"""
    try:
        load_config_file()
        return jsonify({"success": True, "message": "配置已重新加载"})
    except Exception as e:
        logger.exception("重新加载配置失败")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/task/cancel', methods=['POST'])
def cancel_task():
    global current_task_id
    with task_lock:
        if current_task_id and current_task_id in tasks:
            logger.info(f"取消任务 {current_task_id}")
            tasks[current_task_id]['state'] = 'CANCELLED'
            tasks[current_task_id]['result'] = {"message": "任务已手动停止"}
            current_task_id = None
            save_tasks_state()
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
        # 返回当前基础配置，确保包含所有必要的配置项
        logger.info("获取基础配置请求")
        # 创建完整的配置响应对象，包含所有可能需要的配置项
        config_response = {
            "user_id_list": config.get('user_id_list', []),
            "query_list": config.get('query_list', ''),
            "only_crawl_original": config.get('only_crawl_original', 1),
            "since_date": config.get('since_date', 1),
            "start_page": config.get('start_page', 1),
            "write_mode": config.get('write_mode', ['csv', 'sqlite']),
            "original_pic_download": config.get('original_pic_download', 0),
            "retweet_pic_download": config.get('retweet_pic_download', 0),
            "original_video_download": config.get('original_video_download', 0),
            "retweet_video_download": config.get('retweet_video_download', 0),
            "original_live_photo_download": config.get('original_live_photo_download', 0),
            "retweet_live_photo_download": config.get('retweet_live_photo_download', 0),
            "download_comment": config.get('download_comment', 0),
            "comment_max_download_count": config.get('comment_max_download_count', 100),
            "download_repost": config.get('download_repost', 0),
            "repost_max_download_count": config.get('repost_max_download_count', 100),
            "user_id_as_folder_name": config.get('user_id_as_folder_name', 0),
            "remove_html_tag": config.get('remove_html_tag', 1),
            "cookie": config.get('cookie', '')
        }
        
        # 添加额外的配置项，确保前端能获取到所有需要的配置
        if 'mysql_config' in config:
            config_response['mysql_config'] = config['mysql_config']
        if 'mongodb_URI' in config:
            config_response['mongodb_URI'] = config['mongodb_URI']
        
        logger.info(f"返回配置: {config_response.keys()}")
        return jsonify(config_response), 200
    
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

def save_tasks_state():
    """保存任务状态到文件，增强的版本"""
    try:
        # 创建目录（如果不存在）
        tasks_dir = os.path.dirname(TASKS_FILE_PATH)
        if tasks_dir and not os.path.exists(tasks_dir):
            os.makedirs(tasks_dir, exist_ok=True)
            logger.info(f"创建任务状态目录: {tasks_dir}")
        
        # 使用锁保护任务数据的读取
        with task_lock:
            # 创建一个任务数据的深拷贝，避免在保存过程中数据被修改
            tasks_copy = {}
            for task_id, task_data in tasks.items():
                tasks_copy[task_id] = task_data.copy()
            
            tasks_data = {
                'tasks': tasks_copy,
                'current_task_id': current_task_id,
                'last_updated': datetime.now().isoformat()
            }
        
        # 文件写入操作
        temp_file = TASKS_FILE_PATH + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, ensure_ascii=False, indent=2)
        
        # 原子性替换文件，避免写入过程中断导致文件损坏
        os.replace(temp_file, TASKS_FILE_PATH)
        
        logger.info(f"任务状态已成功保存到文件: {TASKS_FILE_PATH}")
        return True
    except PermissionError as pe:
        logger.error(f"保存任务状态失败 - 权限错误: {pe}")
        logger.error(f"检查文件权限: {TASKS_FILE_PATH}")
        return False
    except IOError as ioe:
        logger.error(f"保存任务状态失败 - IO错误: {ioe}")
        return False
    except Exception as e:
        logger.exception(f"保存任务状态失败 - 未预期的错误")
        return False

def load_tasks_state():
    """从文件加载任务状态，增强的版本"""
    global tasks, current_task_id
    try:
        if os.path.exists(TASKS_FILE_PATH):
            # 检查文件大小是否合理
            file_size = os.path.getsize(TASKS_FILE_PATH)
            if file_size > 50 * 1024 * 1024:  # 限制文件大小为50MB
                logger.error(f"任务状态文件过大: {file_size} 字节，跳过加载")
                return False
            
            # 读取文件内容
            with open(TASKS_FILE_PATH, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
            
            # 验证数据格式
            if not isinstance(tasks_data, dict):
                logger.error("任务状态文件格式错误: 不是有效的JSON对象")
                return False
            
            # 获取任务数据，确保是字典类型
            loaded_tasks = tasks_data.get('tasks', {})
            if not isinstance(loaded_tasks, dict):
                logger.error("任务状态文件格式错误: tasks字段不是有效的字典")
                loaded_tasks = {}
            
            # 验证和清理任务数据
            valid_tasks = {}
            for task_id, task_data in loaded_tasks.items():
                if isinstance(task_data, dict):
                    # 确保任务有必要的字段
                    if 'state' not in task_data:
                        task_data['state'] = 'UNKNOWN'
                    if 'progress' not in task_data:
                        task_data['progress'] = 0
                    # 对于正在进行中的任务，确保状态正确
                    if task_data.get('state') == 'PROGRESS' and 'end_time' not in task_data:
                        logger.info(f"恢复进行中任务: {task_id}")
                    valid_tasks[task_id] = task_data
                else:
                    logger.warning(f"跳过无效的任务数据: {task_id}")
            
            # 使用锁保护全局变量的更新
            with task_lock:
                # 先清空现有任务，避免任务重复
                tasks.clear()
                # 加载验证过的任务
                tasks.update(valid_tasks)
                
                # 验证current_task_id是否存在于加载的任务中
                loaded_task_id = tasks_data.get('current_task_id', None)
                if loaded_task_id and loaded_task_id in tasks:
                    task = tasks[loaded_task_id]
                    # 只有任务状态为PROGRESS或PENDING时才恢复为当前任务
                    if task.get('state') in ['PROGRESS', 'PENDING']:
                        current_task_id = loaded_task_id
                        logger.info(f"恢复当前任务ID: {current_task_id}")
                    else:
                        current_task_id = None
                else:
                    # 如果current_task_id无效，查找正在运行的任务
                    current_task_id = None
                    for task_id, task in tasks.items():
                        if task.get('state') in ['PROGRESS', 'PENDING']:
                            current_task_id = task_id
                            logger.info(f"找到并设置当前任务ID: {current_task_id}")
                            break
            
            last_updated = tasks_data.get('last_updated', '未知')
            logger.info(f"任务状态已从文件加载，共 {len(tasks)} 个任务，最后更新时间: {last_updated}")
            return True
        else:
            logger.info(f"任务状态文件不存在: {TASKS_FILE_PATH}")
            return False
    except json.JSONDecodeError as je:
        logger.error(f"任务状态文件JSON解析错误: {je}")
        return False
    except PermissionError as pe:
        logger.error(f"加载任务状态失败 - 权限错误: {pe}")
        return False
    except IOError as ioe:
        logger.error(f"加载任务状态失败 - IO错误: {ioe}")
        return False
    except Exception as e:
        logger.exception(f"加载任务状态失败 - 未预期的错误")
        return False

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
                    save_tasks_state()  # 保存新创建的任务状态
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

@app.route('/<path:filename>')
def serve_html_files(filename):
    """提供HTML文件的路由"""
    if filename.endswith('.html'):
        file_path = os.path.join(BASE_DIR, filename)
        if os.path.exists(file_path):
            return send_from_directory(BASE_DIR, filename)
    # 如果不是HTML文件或文件不存在，返回404
    return '', 404

if __name__ == "__main__":
    # 加载配置
    load_config_file()
    load_tasks_state()  # 启动时加载任务状态
    
    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=schedule_refresh, daemon=True)
    scheduler_thread.start()

    logger.info("服务启动 (直接运行模式)")
    # 使用app.run启动服务
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)  # 关闭reloader避免启动两次，明确指定host和port