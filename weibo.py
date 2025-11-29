#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import copy
import csv
import json
import logging
import logging.config
import math
import os
import random
import re
import sqlite3
import sys
import warnings
import webbrowser
from collections import OrderedDict
from datetime import date, datetime, timedelta
from pathlib import Path
from time import sleep

import requests
from requests.exceptions import RequestException
from lxml import etree
from requests.adapters import HTTPAdapter
from tqdm import tqdm

import const
from util import csvutil
from util.dateutil import convert_to_days_ago
from util.notify import push_deer
from util.llm_analyzer import LLMAnalyzer  # 导入 LLM 分析器

warnings.filterwarnings("ignore")

# 如果日志文件夹不存在，则创建
if not os.path.isdir("log/"):
    os.makedirs("log/")
logging_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + "logging.conf"
logging.config.fileConfig(logging_path)
logger = logging.getLogger("weibo")

# 日期时间格式
DTFORMAT = "%Y-%m-%dT%H:%M:%S"

class Weibo(object):
    def __init__(self, config):
        """Weibo类初始化"""
        # 首先验证并处理配置
        self.validate_config(config)
        
        # 然后将处理后的配置值赋值给实例变量
        self.only_crawl_original = config["only_crawl_original"]  # 取值范围为0、1,程序默认值为0,代表要爬取用户的全部微博,1代表只爬取用户的原创微博
        self.remove_html_tag = config[
            "remove_html_tag"
        ]  # 取值范围为0、1, 0代表不移除微博中的html tag, 1代表移除
        since_date = config["since_date"]
        # since_date 若为整数，则取该天数之前的日期；若为 yyyy-mm-dd，则增加时间
        if isinstance(since_date, int):
            since_date = date.today() - timedelta(since_date)
            since_date = since_date.strftime(DTFORMAT)
        elif self.is_date(since_date):
            since_date = "{}T00:00:00".format(since_date)
        elif self.is_datetime(since_date):
            pass
        else:
            logger.error("since_date 格式不正确，请确认配置是否正确")
            sys.exit()
        self.since_date = since_date  # 起始时间，即爬取发布日期从该值到现在的微博，形式为yyyy-mm-ddThh:mm:ss，如：2023-08-21T09:23:03
        self.start_page = config.get("start_page", 1)  # 开始爬的页，如果中途被限制而结束可以用此定义开始页码
        self.write_mode = config[
            "write_mode"
        ]  # 结果信息保存类型，为list形式，可包含csv、mongo和mysql三种类型
        self.original_pic_download = config[
            "original_pic_download"
        ]  # 取值范围为0、1, 0代表不下载原创微博图片,1代表下载
        self.retweet_pic_download = config[
            "retweet_pic_download"
        ]  # 取值范围为0、1, 0代表不下载转发微博图片,1代表下载
        self.original_video_download = config[
            "original_video_download"
        ]  # 取值范围为0、1, 0代表不下载原创微博视频,1代表下载
        self.retweet_video_download = config[
            "retweet_video_download"
        ]  # 取值范围为0、1, 0代表不下载转发微博视频,1代表下载
        
        # 新增Live Photo视频下载配置
        self.original_live_photo_download = config["original_live_photo_download"]
        self.retweet_live_photo_download = config["retweet_live_photo_download"]
        
        self.download_comment = config["download_comment"]  # 1代表下载评论,0代表不下载
        self.comment_max_download_count = config[
            "comment_max_download_count"
        ]  # 如果设置了下评论，每条微博评论数会限制在这个值内
        self.download_repost = config["download_repost"]  # 1代表下载转发,0代表不下载
        self.repost_max_download_count = config[
            "repost_max_download_count"
        ]  # 如果设置了下转发，每条微博转发数会限制在这个值内
        self.user_id_as_folder_name = config.get(
            "user_id_as_folder_name", 0
        )  # 结果目录名，取值为0或1，决定结果文件存储在用户昵称文件夹里还是用户id文件夹里
        cookie_string = config.get("cookie")  # 微博cookie，可填可不填
        cookies = {}
        for pair in cookie_string.split(';'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        # 增强浏览器行为模拟 - 提供多个User-Agent选项用于随机切换
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36'
        ]
        
        # 随机选择一个User-Agent
        user_agent = random.choice(self.user_agents)
        
        self.headers = {
            'Referer': 'https://weibo.com/',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': user_agent,
            # 添加更多模拟浏览器的头部信息
            'accept-encoding': 'gzip, deflate, br',
            'connection': 'keep-alive',
        }
        
        # 初始化代理IP池支持
        self.proxies = config.get("proxies", [])
        self.current_proxy_index = 0
        
        # 添加指纹信息，模拟真实浏览器
        self.fingerprint = {
            'screen': {'width': 1920, 'height': 1080},  # 模拟常见屏幕分辨率
            'timezone': 'Asia/Shanghai',
            'language': 'zh-CN'
        }
        
        self.mysql_config = config.get("mysql_config")  # MySQL数据库连接配置，可以不填
        self.mongodb_URI = config.get("mongodb_URI")  # MongoDB数据库连接字符串，可以不填
        self.post_config = config.get("post_config")  # post_config，可以不填
        self.page_weibo_count = config.get("page_weibo_count", 10)  # page_weibo_count，爬取一页的微博数，默认10页
        
        # 初始化 LLM 分析器
        self.llm_analyzer = LLMAnalyzer(config) if config.get("llm_config") else None
        
        user_id_list = config["user_id_list"]
        requests_session = requests.Session()
        
        # 配置会话的重试策略
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=3)
        requests_session.mount('http://', adapter)
        requests_session.mount('https://', adapter)
        
        # 设置会话超时
        requests_session.timeout = 15
        
        self.session = requests_session
        self.session.cookies.update(cookies)
        
        # 增加连接池和TCP优化
        self.session.keep_alive = True
        
        # 初始化请求统计信息
        self.request_count = 0
        self.error_count = 0
        self.last_reset_time = datetime.now()
        requests_session.cookies.update(cookies)

        self.session = requests_session
        adapter = HTTPAdapter(max_retries=5)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        # 避免卡住
        if isinstance(user_id_list, list):
            random.shuffle(user_id_list)

        query_list = config.get("query_list") or []
        if isinstance(query_list, str):
            query_list = query_list.split(",")
        self.query_list = query_list
        if not isinstance(user_id_list, list):
            if not os.path.isabs(user_id_list):
                user_id_list = (
                    os.path.split(os.path.realpath(__file__))[0] + os.sep + user_id_list
                )
            self.user_config_file_path = user_id_list  # 用户配置文件路径
            user_config_list = self.get_user_config_list(user_id_list)
        else:
            self.user_config_file_path = ""
            user_config_list = [
                {
                    "user_id": user_id,
                    "since_date": self.since_date,
                    "query_list": query_list,
                }
                for user_id in user_id_list
            ]

        self.user_config_list = user_config_list  # 要爬取的微博用户的user_config列表
        self.user_config = {}  # 用户配置,包含用户id和since_date
        self.start_date = ""  # 获取用户第一条微博时的日期
        self.query = ""
        self.user = {}  # 存储目标微博用户信息
        self.got_count = 0  # 存储爬取到的微博数
        self.weibo = []  # 存储爬取到的所有微博信息
        self.weibo_id_list = []  # 存储爬取到的所有微博id
        self.long_sleep_count_before_each_user = 0 #每个用户前的长时间sleep避免被ban
        self.store_binary_in_sqlite = config.get("store_binary_in_sqlite", 0)
    def validate_config(self, config):
        """验证配置是否正确"""

        # 验证如下1/0相关值
        # 基础必要参数列表
        base_arguments = [
            "only_crawl_original",
            "original_pic_download",
            "retweet_pic_download",
            "original_video_download",
            "retweet_video_download",
            "download_comment",
            "download_repost",
        ]
        
        # 可选参数列表，可能不存在于配置中
        optional_arguments = [
            "original_live_photo_download", 
            "retweet_live_photo_download", 
        ]
        
        # 为可选参数设置默认值（如果不存在）
        for argument in optional_arguments:
            if argument not in config:
                config[argument] = 0
                logger.info(f"为 {argument} 设置默认值 0")
        
        # 验证所有参数
        all_arguments = base_arguments + optional_arguments
        for argument in all_arguments:
            # 处理字符串类型的"0"和"1"
            value = config[argument]
            # 转换为字符串进行比较
            if str(value) not in ['0', '1']:
                logger.warning("%s值应为0或1,请重新输入", value)
                sys.exit()
            # 将字符串转换为整数
            config[argument] = int(value)

        # 验证query_list
        query_list = config.get("query_list") or []
        if (not isinstance(query_list, list)) and (not isinstance(query_list, str)):
            logger.warning("query_list值应为list类型或字符串,请重新输入")
            sys.exit()

        # 验证write_mode
        write_mode = ["csv", "json", "mongo", "mysql", "sqlite", "post"]
        if not isinstance(config["write_mode"], list):
            sys.exit("write_mode值应为list类型")
        for mode in config["write_mode"]:
            if mode not in write_mode:
                logger.warning(
                    "%s为无效模式，请从csv、json、mongo和mysql中挑选一个或多个作为write_mode", mode
                )
                sys.exit()
        # 验证运行模式
        if "sqlite" not in config["write_mode"] and const.MODE == "append":
            logger.warning("append模式下请将sqlite加入write_mode中")
            sys.exit()

        # 验证user_id_list
        user_id_list = config["user_id_list"]
        if (not isinstance(user_id_list, list)) and (not user_id_list.endswith(".txt")):
            logger.warning("user_id_list值应为list类型或txt文件路径")
            sys.exit()
        if not isinstance(user_id_list, list):
            if not os.path.isabs(user_id_list):
                user_id_list = (
                    os.path.split(os.path.realpath(__file__))[0] + os.sep + user_id_list
                )
            if not os.path.isfile(user_id_list):
                logger.warning("不存在%s文件", user_id_list)
                sys.exit()

        # 验证since_date
        since_date = config["since_date"]
        # 处理字符串形式的数字
        if isinstance(since_date, str) and since_date.isdigit():
            # 转换为整数
            since_date = int(since_date)
            config["since_date"] = since_date
        
        # 如果是整数，转换为日期格式
        if isinstance(since_date, int):
            # 将天数转换为具体日期
            days_ago = date.today() - timedelta(days=since_date)
            config["since_date"] = days_ago.strftime(DTFORMAT)
            logger.info(f"since_date设置为{since_date}天前: {config['since_date']}")
        # 验证日期格式
        elif not self.is_datetime(since_date) and not self.is_date(since_date):
            logger.warning("since_date值应为yyyy-mm-dd形式、yyyy-mm-ddTHH:MM:SS形式或整数，请重新输入")
            # 自动设置为7天前
            logger.info("自动设置since_date为7天前")
            days_ago = date.today() - timedelta(days=7)
            config["since_date"] = days_ago.strftime(DTFORMAT)

        comment_max_count = config["comment_max_download_count"]
        if not isinstance(comment_max_count, int):
            logger.warning("最大下载评论数 (comment_max_download_count) 应为整数类型")
            sys.exit()
        elif comment_max_count < 0:
            logger.warning("最大下载评论数 (comment_max_download_count) 应该为正整数")
            sys.exit()

        repost_max_count = config["repost_max_download_count"]
        if not isinstance(repost_max_count, int):
            logger.warning("最大下载转发数 (repost_max_download_count) 应为整数类型")
            sys.exit()
        elif repost_max_count < 0:
            logger.warning("最大下载转发数 (repost_max_download_count) 应该为正整数")
            sys.exit()

    def is_datetime(self, since_date):
        """判断日期格式是否为 %Y-%m-%dT%H:%M:%S"""
        try:
            datetime.strptime(since_date, DTFORMAT)
            return True
        except ValueError:
            return False
    
    def is_date(self, since_date):
        """判断日期格式是否为 %Y-%m-%d"""
        try:
            datetime.strptime(since_date, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def get_json(self, params):
        url = "https://m.weibo.cn/api/container/getIndex?"
        try:
            # 增加随机延迟时间（2-5秒）
            sleep_time = random.uniform(2, 5)
            logger.debug(f"请求前随机延迟 {sleep_time:.2f} 秒")
            sleep(sleep_time)
            
            # 每10个请求随机切换User-Agent
            self.request_count += 1
            if self.request_count % 10 == 0:
                self.headers['user-agent'] = random.choice(self.user_agents)
                logger.debug(f"已切换User-Agent: {self.headers['user-agent']}")
                
                # 每30分钟重置请求计数，避免被长时间跟踪
                current_time = datetime.now()
                if (current_time - self.last_reset_time).total_seconds() > 1800:
                    self.request_count = 0
                    self.last_reset_time = current_time
                    logger.info("已重置请求计数")
            
            # 获取代理（如果有）
            proxy = self.get_next_proxy() if self.proxies else None
            
            # 发送请求，添加verify=False以避免SSL验证问题
            r = self.session.get(url, params=params, headers=self.headers, 
                                proxies=proxy, verify=False, timeout=15)
            r.raise_for_status()
            
            # 检查响应内容是否为有效的JSON
            content_type = r.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                logger.warning(f"非JSON响应: {content_type}")
                
            response_json = r.json()
            # 重置错误计数
            self.error_count = 0
            return response_json, r.status_code
        except RequestException as e:
            self.error_count += 1
            # 如果连续错误次数超过5次，尝试切换代理
            if self.error_count >= 5 and self.proxies:
                logger.warning(f"连续{self.error_count}次请求失败，强制切换代理")
                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            logger.error(f"请求失败，错误信息：{e}")
            return {}, 500
        except ValueError as ve:
            self.error_count += 1
            logger.error(f"JSON 解码失败，错误信息：{ve}")
            return {}, 500
        except Exception as ex:
            self.error_count += 1
            logger.error(f"未预期的错误：{ex}")
            return {}, 500

    def handle_captcha(self, js):
        """
        处理验证码挑战，提示用户手动完成验证。

        参数:
            js (dict): API 返回的 JSON 数据。

        返回:
            bool: 如果用户成功完成验证码，返回 True；否则返回 False。
        """
        logger.debug(f"收到的 JSON 数据：{js}")
        
        captcha_url = js.get("url")
        if captcha_url:
            logger.warning("检测到验证码挑战。正在打开验证码页面以供手动验证。")
            webbrowser.open(captcha_url)
        else:
            logger.warning("检测到可能的验证码挑战，但未提供验证码 URL。请手动检查浏览器并完成验证码验证。")
            return False
        
        logger.info("请在打开的浏览器窗口中完成验证码验证。")
        while True:
            try:
                # 等待用户输入
                user_input = input("完成验证码后，请输入 'y' 继续，或输入 'q' 退出：").strip().lower()

                if user_input == 'y':
                    logger.info("用户输入 'y'，继续爬取。")
                    return True
                elif user_input == 'q':
                    logger.warning("用户选择退出，程序中止。")
                    sys.exit("用户选择退出，程序中止。")
                else:
                    logger.warning("无效输入，请重新输入 'y' 或 'q'。")
            except EOFError:
                logger.error("读取用户输入时发生 EOFError，程序退出。")
                sys.exit("输入流已关闭，程序中止。")
    
    def get_weibo_json(self, page):
        """获取网页中微博json数据"""
        url = "https://m.weibo.cn/api/container/getIndex?"
        params = (
            {
                "container_ext": "profile_uid:" + str(self.user_config["user_id"]),
                "containerid": "100103type=401&q=" + self.query,
                "page_type": "searchall",
            }
            if self.query
            else {"containerid": "230413" + str(self.user_config["user_id"])}
        )
        params["page"] = page
        params["count"] = self.page_weibo_count
        max_retries = 8  # 增加最大重试次数
        retries = 0
        backoff_factor = 5
        
        # 智能重试策略配置
        retry_strategies = {
            432: {"max_retries": 10, "backoff_base": 3, "switch_proxy": True},
            429: {"max_retries": 8, "backoff_base": 2, "switch_proxy": True},
            403: {"max_retries": 5, "backoff_base": 1, "switch_proxy": False},
            500: {"max_retries": 3, "backoff_base": 1, "switch_proxy": False}
        }
        
        while retries < max_retries:
            try:
                # 进一步增加随机延迟时间范围（3-8秒）
                sleep_time = random.uniform(3, 8)
                logger.debug(f"获取微博数据前随机延迟 {sleep_time:.2f} 秒")
                sleep(sleep_time)
                
                # 获取当前代理
                proxy = self.get_next_proxy() if self.proxies else None
                
                response = self.session.get(url, params=params, headers=self.headers, 
                                          proxies=proxy, timeout=15)
                
                # 特殊错误处理
                if response.status_code in retry_strategies:
                    strategy = retry_strategies[response.status_code]
                    
                    # 根据不同错误类型使用不同的重试策略
                    if retries < strategy["max_retries"]:
                        retries += 1
                        
                        # 对于432错误的智能恢复机制
                        if response.status_code == 432:
                            logger.warning(f"遇到432错误（第{retries}次），可能被反爬系统识别。应用智能恢复策略...")
                            
                            # 1. 切换User-Agent
                            old_ua = self.headers['user-agent']
                            while old_ua == self.headers['user-agent']:
                                self.headers['user-agent'] = random.choice(self.user_agents)
                            logger.info(f"已切换User-Agent")
                            
                            # 2. 增加等待时间（指数退避 + 随机抖动）
                            base_wait = strategy["backoff_base"] ** retries
                            jitter = random.uniform(0.5, 1.5)
                            wait_time = base_wait * jitter * backoff_factor
                            
                            # 3. 如果配置了代理，切换代理
                            if strategy["switch_proxy"] and self.proxies:
                                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
                                logger.info(f"已切换至代理 {self.current_proxy_index + 1}/{len(self.proxies)}")
                            
                            # 4. 添加随机等待时间，避免规律性
                            random_wait = random.uniform(5, 15)
                            total_wait = wait_time + random_wait
                            
                            logger.info(f"432 Client Error，等待 {total_wait:.2f} 秒后重试（基础: {wait_time:.2f}s + 随机: {random_wait:.2f}s）...")
                            sleep(total_wait)
                            continue
                        else:
                            # 其他错误类型的处理
                            logger.warning(f"遇到{response.status_code}错误，等待后重试...")
                            wait_time = strategy["backoff_base"] ** retries * backoff_factor
                            logger.error(f"{response.status_code} Error，等待 {wait_time} 秒后重试...")
                            sleep(wait_time)
                            continue
                    else:
                        logger.error(f"达到{response.status_code}错误的最大重试次数")
                        return {}
                
                # 正常状态码检查
                response.raise_for_status()  # 如果响应状态码不是 200，会抛出 HTTPError
                
                # 检查响应内容是否为空
                if not response.content:
                    logger.warning("响应内容为空")
                    retries += 1
                    sleep(backoff_factor * (2 ** retries))
                    continue
                
                try:
                    js = response.json()
                except ValueError:
                    logger.warning("响应不是有效的JSON格式")
                    retries += 1
                    sleep(backoff_factor * (2 ** retries))
                    continue
                
                if 'data' in js:
                    logger.info(f"成功获取到页面 {page} 的数据。")
                    # 重置重试计数
                    retries = 0
                    return js
                else:
                    logger.warning("未能获取到数据，可能需要验证码验证。")
                    if self.handle_captcha(js):
                        logger.info("用户已完成验证码验证，继续请求数据。")
                        retries = 0  # 重置重试计数器
                        continue
                    else:
                        logger.warning("验证码验证失败或未完成，跳过当前页面。")
                        return {}
            except RequestException as e:
                retries += 1
                sleep_time = backoff_factor * (2 ** retries)
                logger.error(f"请求失败，错误信息：{e}。等待 {sleep_time} 秒后重试...")
                sleep(sleep_time)
            except ValueError as ve:
                retries += 1
                sleep_time = backoff_factor * (2 ** retries)
                logger.error(f"JSON 解码失败，错误信息：{ve}。等待 {sleep_time} 秒后重试...")
                sleep(sleep_time)
            except Exception as e:
                retries += 1
                sleep_time = backoff_factor * (2 ** retries)
                logger.error(f"发生未知错误：{e}。等待 {sleep_time} 秒后重试...")
                sleep(sleep_time)
        
        logger.warning("超过最大重试次数，跳过当前页面。")
        return {}
    
    def user_to_csv(self):
        """将爬取到的用户信息写入csv文件"""
        file_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "weibo"
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)
        file_path = file_dir + os.sep + "users.csv"
        self.user_csv_file_path = file_path
        result_headers = [
            "用户id",
            "昵称",
            "性别",
            "生日",
            "所在地",
            "学习经历",
            "公司",
            "注册时间",
            "阳光信用",
            "微博数",
            "粉丝数",
            "关注数",
            "简介",
            "主页",
            "头像",
            "高清头像",
            "微博等级",
            "会员等级",
            "是否认证",
            "认证类型",
            "认证信息",
            "上次记录微博信息",
        ]
        result_data = [
            [
                v.encode("utf-8") if "unicode" in str(type(v)) else v
                for v in self.user.values()
            ]
        ]
        # 已经插入信息的用户无需重复插入，返回的id是空字符串或微博id 发布日期%Y-%m-%d
        last_weibo_msg = csvutil.insert_or_update_user(
            logger, result_headers, result_data, file_path
        )
        self.last_weibo_id = last_weibo_msg.split(" ")[0] if last_weibo_msg else ""
        self.last_weibo_date = (
            last_weibo_msg.split(" ")[1]
            if last_weibo_msg
            else self.user_config["since_date"]
        )

    def user_to_mongodb(self):
        """将爬取的用户信息写入MongoDB数据库"""
        user_list = [self.user]
        self.info_to_mongodb("user", user_list)
        logger.info("%s信息写入MongoDB数据库完毕", self.user["screen_name"])

    def user_to_mysql(self):
        """将爬取的用户信息写入MySQL数据库"""
        # 使用实例中的mysql_config配置
        mysql_config = self.mysql_config if self.mysql_config else {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "123456",
            "charset": "utf8mb4",
        }
        # 创建'weibo'数据库
        create_database = """CREATE DATABASE IF NOT EXISTS weibo DEFAULT
                         CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"""
        self.mysql_create_database(mysql_config, create_database)
        # 创建'user'表
        create_table = """
                CREATE TABLE IF NOT EXISTS user (
                id varchar(20) NOT NULL,
                screen_name varchar(30),
                gender varchar(10),
                statuses_count INT,
                followers_count INT,
                follow_count INT,
                registration_time varchar(20),
                sunshine varchar(20),
                birthday varchar(40),
                location varchar(200),
                education varchar(200),
                company varchar(200),
                description varchar(400),
                profile_url varchar(200),
                profile_image_url varchar(200),
                avatar_hd varchar(200),
                urank INT,
                mbrank INT,
                verified BOOLEAN DEFAULT 0,
                verified_type INT,
                verified_reason varchar(140),
                PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        self.mysql_create_table(mysql_config, create_table)
        self.mysql_insert(mysql_config, "user", [self.user])
        logger.info("%s信息写入MySQL数据库完毕", self.user["screen_name"])

    def user_to_database(self):
        """将用户信息写入文件/数据库"""
        self.user_to_csv()
        if "mysql" in self.write_mode:
            self.user_to_mysql()
        if "mongo" in self.write_mode:
            self.user_to_mongodb()
        if "sqlite" in self.write_mode:
            self.user_to_sqlite()

    def get_user_info(self):
        """获取用户信息"""
        params = {"containerid": "100505" + str(self.user_config["user_id"])}
        url = "https://m.weibo.cn/api/container/getIndex"
        
        # 这里在读取下一个用户的时候很容易被ban，需要优化休眠时长
        # 加一个count，不需要一上来啥都没干就sleep
        if self.long_sleep_count_before_each_user > 0:
            sleep_time = random.randint(30, 60)
            # 添加log，否则一般用户不知道以为程序卡了
            logger.info(f"""短暂sleep {sleep_time}秒，避免被ban""")        
            sleep(sleep_time)
            logger.info("sleep结束")  
        self.long_sleep_count_before_each_user = self.long_sleep_count_before_each_user + 1      

        max_retries = 5  # 设置最大重试次数，避免无限循环
        retries = 0
        backoff_factor = 5  # 指数退避的基数（秒）
        
        while retries < max_retries:
            try:
                response = self.session.get(url, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                js = response.json()
                if 'data' in js and 'userInfo' in js['data']:
                    info = js["data"]["userInfo"]
                    user_info = OrderedDict()
                    user_info["id"] = self.user_config["user_id"]
                    user_info["screen_name"] = info.get("screen_name", "")
                    user_info["gender"] = info.get("gender", "")
                    params = {
                        "containerid": "230283" + str(self.user_config["user_id"]) + "_-_INFO"
                    }
                    zh_list = ["生日", "所在地", "小学", "初中", "高中", "大学", "公司", "注册时间", "阳光信用"]
                    en_list = [
                        "birthday",
                        "location",
                        "education",
                        "education",
                        "education",
                        "education",
                        "company",
                        "registration_time",
                        "sunshine",
                    ]
                    for i in en_list:
                        user_info[i] = ""
                    js, _ = self.get_json(params)
                    if js["ok"]:
                        cards = js["data"]["cards"]
                        if isinstance(cards, list) and len(cards) > 1:
                            card_list = cards[0]["card_group"] + cards[1]["card_group"]
                            for card in card_list:
                                if card.get("item_name") in zh_list:
                                    user_info[
                                        en_list[zh_list.index(card.get("item_name"))]
                                    ] = card.get("item_content", "")
                    user_info["statuses_count"] = self.string_to_int(
                        info.get("statuses_count", 0)
                    )
                    user_info["followers_count"] = self.string_to_int(
                        info.get("followers_count", 0)
                    )
                    user_info["follow_count"] = self.string_to_int(info.get("follow_count", 0))
                    user_info["description"] = info.get("description", "")
                    user_info["profile_url"] = info.get("profile_url", "")
                    user_info["profile_image_url"] = info.get("profile_image_url", "")
                    user_info["avatar_hd"] = info.get("avatar_hd", "")
                    user_info["urank"] = info.get("urank", 0)
                    user_info["mbrank"] = info.get("mbrank", 0)
                    user_info["verified"] = info.get("verified", False)
                    user_info["verified_type"] = info.get("verified_type", -1)
                    user_info["verified_reason"] = info.get("verified_reason", "")
                    self.user = self.standardize_info(user_info)
                    self.user_to_database()
                    logger.info(f"成功获取到用户 {self.user_config['user_id']} 的信息。")
                    return 0
                else:
                    logger.warning("未能获取到用户信息，可能需要验证码验证。")
                    if self.handle_captcha(js):
                        logger.info("用户已完成验证码验证，继续请求用户信息。")
                        retries = 0  # 重置重试计数器
                        continue
                    else:
                        logger.error("验证码验证失败或未完成，程序将退出。")
                        sys.exit()
            except RequestException as e:
                retries += 1
                sleep_time = backoff_factor * (2 ** retries)
                logger.error(f"请求失败，错误信息：{e}。等待 {sleep_time} 秒后重试...")
                sleep(sleep_time)
            except ValueError as ve:
                retries += 1
                sleep_time = backoff_factor * (2 ** retries)
                logger.error(f"JSON 解码失败，错误信息：{ve}。等待 {sleep_time} 秒后重试...")
                sleep(sleep_time)
        logger.error("超过最大重试次数，程序将退出。")
        sys.exit("超过最大重试次数，程序已退出。")

    def get_long_weibo(self, id):
        """获取长微博"""
        url = "https://m.weibo.cn/detail/%s" % id
        logger.info(f"""URL: {url} """)
        for i in range(5):
            sleep(random.uniform(1.0, 2.5))
            html = self.session.get(url, headers=self.headers, verify=False).text
            html = html[html.find('"status":') :]
            html = html[: html.rfind('"call"')]
            html = html[: html.rfind(",")]
            html = "{" + html + "}"
            js = json.loads(html, strict=False)
            weibo_info = js.get("status")
            if weibo_info:
                weibo = self.parse_weibo(weibo_info)
                return weibo

    def get_pics(self, weibo_info):
        """获取微博原始图片url"""
        if weibo_info.get("pics"):
            pic_info = weibo_info["pics"]
            pic_list = [pic["large"]["url"] for pic in pic_info]
            pics = ",".join(pic_list)
        else:
            pics = ""
        return pics


    def get_live_photo_url(self, weibo_info):
        """获取Live Photo视频URL"""
        live_photo_list = weibo_info.get("live_photo", [])
        return ";".join(live_photo_list) if live_photo_list else ""
    def get_video_url(self, weibo_info):
        """获取微博普通视频URL"""
        video_url = ""
        if weibo_info.get("page_info"):
            if weibo_info["page_info"].get("type") == "video":
                media_info = weibo_info["page_info"].get("urls") or weibo_info["page_info"].get("media_info")
                if media_info:
                    video_url = (media_info.get("mp4_720p_mp4") or
                                media_info.get("mp4_hd_url") or
                                media_info.get("hevc_mp4_hd") or
                                media_info.get("mp4_sd_url") or
                                media_info.get("mp4_ld_mp4") or
                                media_info.get("stream_url_hd") or
                                media_info.get("stream_url"))
        return video_url

    def get_next_proxy(self):
        """获取下一个代理IP"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        logger.debug(f"使用代理: {proxy}")
        return proxy
        
    def download_one_file(self, url, file_path, type, weibo_id):
        """下载单个文件"""
        # 检查文件是否已存在
        if os.path.exists(file_path):
            logger.info(f"文件 {file_path} 已存在，跳过下载")
            return True
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 配置会话
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=0)  # 禁用默认重试，使用自定义重试逻辑
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # 设置更真实的浏览器头部
        file_headers = copy.deepcopy(self.headers)
        file_headers['accept'] = 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
        file_headers['sec-fetch-dest'] = 'image'  # 对于图片请求
        file_headers['user-agent'] = random.choice(self.user_agents)  # 每次下载使用随机User-Agent
        
        max_retries = 8  # 增加下载重试次数
        retries = 0
        backoff_factor = 3
        success = False
        
        # 智能下载重试策略
        download_strategies = {
            432: {"max_retries": 10, "backoff_base": 2.5, "switch_proxy": True, "long_pause": True},
            429: {"max_retries": 8, "backoff_base": 2, "switch_proxy": True, "long_pause": False},
            403: {"max_retries": 5, "backoff_base": 1.5, "switch_proxy": True, "long_pause": False},
            500: {"max_retries": 3, "backoff_base": 1, "switch_proxy": False, "long_pause": False}
        }
        
        while retries < max_retries and not success:
            try:
                # 下载前随机延迟（2-6秒）
                sleep_time = random.uniform(2, 6)
                logger.debug(f"下载 {url} 前随机延迟 {sleep_time:.2f} 秒")
                sleep(sleep_time)
                
                # 获取当前代理
                proxy = self.get_next_proxy() if self.proxies else None
                
                # 流式下载大文件
                with session.get(url, headers=file_headers, stream=True, 
                               proxies=proxy, timeout=30, verify=False) as response:
                    # 检查响应状态码
                    status_code = response.status_code
                    
                    # 针对不同错误状态码采取相应策略
                    if status_code in download_strategies:
                        strategy = download_strategies[status_code]
                        
                        if retries < strategy["max_retries"]:
                            retries += 1
                            logger.warning(f"下载文件遇到{status_code}错误（第{retries}次）")
                            
                            # 应用策略
                            if strategy["switch_proxy"] and self.proxies:
                                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
                                logger.info(f"已切换代理")
                            
                            # 计算等待时间（指数退避 + 随机抖动）
                            base_wait = strategy["backoff_base"] ** min(retries, 5)  # 限制最大等待时间增长
                            jitter = random.uniform(0.7, 1.3)
                            wait_time = base_wait * jitter * backoff_factor
                            
                            # 对于特殊情况，增加长时间暂停
                            if strategy["long_pause"] and retries >= 3:
                                long_wait = random.uniform(30, 60)
                                logger.warning(f"触发长时间暂停策略，额外等待 {long_wait:.2f} 秒...")
                                wait_time += long_wait
                            
                            logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                            sleep(wait_time)
                            continue
                        else:
                            logger.error(f"达到{status_code}错误的最大重试次数")
                            break
                    
                    # 检查是否成功
                    response.raise_for_status()
                    
                    # 获取文件大小进行进度显示
                    total_size = int(response.headers.get('content-length', 0))
                    
                    # 确定文件扩展名
                    content_type = response.headers.get('content-type', '')
                    extension = os.path.splitext(file_path)[1]
                    
                    # 如果没有扩展名或者需要根据内容类型修正扩展名
                    if not extension or extension.lower() == '.unknown':
                        # 根据Content-Type确定扩展名
                        mime_to_extension = {
                            'image/jpeg': '.jpg',
                            'image/png': '.png',
                            'image/gif': '.gif',
                            'image/webp': '.webp',
                            'image/bmp': '.bmp',
                            'video/mp4': '.mp4',
                            'video/quicktime': '.mov',
                            'application/octet-stream': '.dat'
                        }
                        
                        if content_type in mime_to_extension:
                            extension = mime_to_extension[content_type]
                            # 更新文件路径
                            file_path = os.path.splitext(file_path)[0] + extension
                            logger.info(f"根据Content-Type修正文件扩展名: {extension}")
                    
                    # 下载文件并写入
                    chunk_size = 8192  # 8KB chunks
                    with open(file_path, 'wb') as f:
                        downloaded_size = 0
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                    
                    # 验证文件是否成功下载
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        success = True
                        logger.info(f"文件 {file_path} 下载成功，大小: {os.path.getsize(file_path)} 字节")
                        
                        # 重置重试计数
                        retries = 0
                        break
                    else:
                        logger.warning(f"文件下载后为空或不存在")
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        retries += 1
                        sleep(backoff_factor * (2 ** retries))
                        continue
            
            except RequestException as e:
                retries += 1
                self.error_count += 1
                
                # 处理连接错误
                if 'Connection' in str(e) or 'timeout' in str(e).lower():
                    logger.error(f"连接错误或超时: {e}")
                    # 遇到连接错误时切换代理
                    if self.proxies:
                        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
                        logger.info(f"已切换代理")
                
                logger.error(f"下载文件异常: {e}，第{retries}次重试")
                
                # 指数退避 + 随机抖动
                wait_time = backoff_factor * (2 ** min(retries, 5)) * random.uniform(0.8, 1.2)
                logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                sleep(wait_time)
                
                # 如果连续下载错误，采取更严格的策略
                if self.error_count >= 8:
                    long_wait = random.uniform(45, 90)
                    logger.warning(f"连续下载错误次数过多，执行长时间暂停 {long_wait:.2f} 秒...")
                    sleep(long_wait)
                    self.error_count = 0
                    # 更换User-Agent
                    file_headers['user-agent'] = random.choice(self.user_agents)
            
            except KeyboardInterrupt:
                logger.warning("下载被用户中断")
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise
            
            except Exception as ex:
                retries += 1
                logger.error(f"下载文件时发生未预期的错误: {ex}")
                
                # 清理可能的不完整文件
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                sleep(backoff_factor * (2 ** min(retries, 5)))
        
        # 如果下载失败，尝试删除可能的不完整文件
        if not success and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"删除不完整的文件: {file_path}")
            except:
                pass
        
        return success

    def sqlite_exist_file(self, url):
        if not os.path.exists(self.get_sqlte_path()):
            return True
        con = self.get_sqlite_connection()
        cur = con.cursor()

        query_sql = """SELECT url FROM bins WHERE path=? """
        count = cur.execute(query_sql, (url,)).fetchone()
        con.close()
        if count is None:
            return False

        return True

    def insert_file_sqlite(self, file_path, weibo_id, url, binary):
        if not weibo_id:
            return
        if self.store_binary_in_sqlite != 1:  # 新增配置判断
            return
        extension = Path(file_path).suffix
        if not extension:
            return
        if len(binary) <= 0:
            return

        file_data = OrderedDict()
        file_data["weibo_id"] = weibo_id
        file_data["ext"] = extension
        file_data["data"] = binary  # 仅当启用时存储二进制
        file_data["path"] = file_path
        file_data["url"] = url

        con = self.get_sqlite_connection()
        self.sqlite_insert(con, file_data, "bins")
        con.close()

    def handle_download(self, file_type, file_dir, urls, w):
        """处理下载相关操作 - 增强版，包含错误处理和重试机制"""
        file_prefix = w["created_at"][:11].replace("-", "") + "_" + str(w["id"])
        success_count = 0
        total_count = 0
        failed_urls = []
        
        # 确保目录存在
        os.makedirs(file_dir, exist_ok=True)
        
        # 根据文件类型和URL格式处理下载
        if file_type == "img":
            url_list = urls.split(",") if "," in urls else [urls]
            total_count = len(url_list)
            
            for i, url in enumerate(url_list):
                # 生成文件名
                index = url.rfind(".")
                if len(url) - index >= 5 or index == -1:
                    file_suffix = ".jpg"
                else:
                    file_suffix = url[index:]
                file_name = file_prefix + "_" + str(i + 1) + file_suffix if len(url_list) > 1 else file_prefix + file_suffix
                file_path = os.path.join(file_dir, file_name)
                
                # 添加下载前的随机延迟
                sleep_time = random.uniform(1.0, 3.0)
                logger.debug(f"图片下载前延迟 {sleep_time:.2f} 秒")
                sleep(sleep_time)
                
                # 执行下载并处理结果
                try:
                    if self.download_one_file(url, file_path, file_type, w["id"]):
                        success_count += 1
                    else:
                        failed_urls.append((url, file_path))
                except Exception as e:
                    logger.error(f"下载图片 {url} 时发生异常: {e}")
                    failed_urls.append((url, file_path))
        
        elif file_type == "video" or file_type == "live_photo":
            url_list = urls.split(";" if ";" in urls else ",")
            total_count = len(url_list)
            
            for i, url in enumerate(url_list):
                # 生成文件名
                file_suffix = ".mov" if url.endswith(".mov") else ".mp4"
                file_name = file_prefix + "_" + str(i + 1) + file_suffix if len(url_list) > 1 else file_prefix + file_suffix
                file_path = os.path.join(file_dir, file_name)
                
                # 添加下载前的随机延迟（视频下载前延迟更长）
                sleep_time = random.uniform(2.0, 5.0)
                logger.debug(f"{file_type}下载前延迟 {sleep_time:.2f} 秒")
                sleep(sleep_time)
                
                # 执行下载并处理结果
                try:
                    if self.download_one_file(url, file_path, file_type, w["id"]):
                        success_count += 1
                    else:
                        failed_urls.append((url, file_path))
                except Exception as e:
                    logger.error(f"下载{file_type} {url} 时发生异常: {e}")
                    failed_urls.append((url, file_path))
        
        # 重试失败的下载
        if failed_urls:
            logger.info(f"准备重试下载失败的{file_type}文件，共{len(failed_urls)}个")
            
            # 等待一段时间后再重试
            retry_delay = random.uniform(5, 10)
            logger.info(f"等待 {retry_delay:.2f} 秒后开始重试")
            sleep(retry_delay)
            
            # 逐个重试，避免并发
            for url, file_path in failed_urls[:]:  # 使用切片创建副本，避免在循环中修改列表
                logger.info(f"正在重试下载 {url}")
                
                try:
                    # 增加重试前的延迟，比首次下载更长
                    retry_sleep = random.uniform(3.0, 8.0)
                    logger.debug(f"重试前延迟 {retry_sleep:.2f} 秒")
                    sleep(retry_sleep)
                    
                    # 尝试切换User-Agent
                    old_ua = self.headers['user-agent']
                    while old_ua == self.headers['user-agent'] and len(self.user_agents) > 1:
                        self.headers['user-agent'] = random.choice(self.user_agents)
                    logger.debug(f"已切换User-Agent用于重试")
                    
                    if self.download_one_file(url, file_path, file_type, w["id"]):
                        success_count += 1
                        failed_urls.remove((url, file_path))
                        logger.info(f"重试下载成功 {url}")
                    else:
                        logger.error(f"重试下载失败 {url}")
                except Exception as e:
                    logger.error(f"重试下载 {url} 时发生异常: {e}")
        
        # 记录下载统计信息
        logger.info(f"{file_type}文件下载完成 - 总数: {total_count}, 成功: {success_count}, 失败: {len(failed_urls)}")
        
        # 如果所有下载都失败，可以考虑进一步的策略
        if success_count == 0 and total_count > 0:
            logger.warning(f"所有{total_count}个{file_type}文件下载失败，可能需要检查网络或代理设置")
            
            # 可以在这里添加更激进的重试策略，比如等待更长时间后再试
            if len(failed_urls) <= 3:  # 只对少量失败文件进行最后一次重试
                final_retry_delay = random.uniform(30, 60)
                logger.info(f"执行最终重试，等待 {final_retry_delay:.2f} 秒...")
                sleep(final_retry_delay)
                
                for url, file_path in failed_urls[:]:
                    logger.info(f"最终尝试下载 {url}")
                    try:
                        if self.download_one_file(url, file_path, file_type, w["id"]):
                            success_count += 1
                            failed_urls.remove((url, file_path))
                    except Exception as e:
                        logger.error(f"最终重试失败 {url}: {e}")
        
        return success_count > 0  # 只要有一个成功就返回True

    def download_files(self, file_type, weibo_type, wrote_count):
        logger.info(f"进入download_files函数: file_type={file_type}, weibo_type={weibo_type}, wrote_count={wrote_count}")
        try:
            describe = ""
            if file_type == "img":
                describe = "图片"
                key = "pics"
            elif file_type == "video":
                describe = "视频"
                key = "video_url"
            elif file_type == "live_photo":
                describe = "Live Photo视频"
                key = "live_photo_url"
            else:
                logger.error("不支持的文件类型: %s", file_type)
                return
            
            if weibo_type == "original":
                describe = "原创微博" + describe
            else:
                describe = "转发微博" + describe
            
            logger.info("即将进行%s下载", describe)
            file_dir = self.get_filepath(file_type)
            file_dir = file_dir + os.sep + describe
            logger.info(f"文件保存路径: {file_dir}")
            
            # 检查是否有文件需要下载
            has_files = False
            total_weibo = len(self.weibo[wrote_count:])
            logger.info(f"需要处理的微博数量: {total_weibo}")
            
            for w in self.weibo[wrote_count:]:
                if weibo_type == "retweet":
                    if w.get("retweet"):
                        w = w["retweet"]
                    else:
                        continue
                if w.get(key):
                    has_files = True
                    logger.info(f"发现可下载文件: 微博ID={w.get('id')}, {key}={w.get(key)}")
                    break
            
            if has_files:
                logger.info("开始准备下载文件...")
                if not os.path.isdir(file_dir):
                    logger.info("创建目录: %s", file_dir)
                    os.makedirs(file_dir)
                else:
                    logger.info("目录已存在: %s", file_dir)
                
                logger.info("开始遍历微博进行下载...")
                downloaded_count = 0
                for w in tqdm(self.weibo[wrote_count:], desc="Download progress"):
                    if weibo_type == "retweet":
                        if w.get("retweet"):
                            w = w["retweet"]
                        else:
                            continue
                    if w.get(key):
                        logger.info(f"开始处理微博: ID={w.get('id')}, 内容={w.get(key)}")
                        self.handle_download(file_type, file_dir, w.get(key), w)
                        downloaded_count += 1
                
                logger.info("%s下载完毕, 共下载%d个文件, 保存路径:", describe, downloaded_count)
                logger.info(file_dir)
            else:
                logger.info("没有%s需要下载", describe)
        except Exception as e:
            logger.error("下载过程中发生错误: %s", str(e))
            logger.exception(e)

    def get_location(self, selector):
        """获取微博发布位置"""
        location_icon = "timeline_card_small_location_default.png"
        span_list = selector.xpath("//span")
        location = ""
        for i, span in enumerate(span_list):
            if span.xpath("img/@src"):
                if location_icon in span.xpath("img/@src")[0]:
                    location = span_list[i + 1].xpath("string(.)")
                    break
        return location

    def get_article_url(self, selector):
        """获取微博中头条文章的url"""
        article_url = ""
        text = selector.xpath("string(.)")
        if text.startswith("发布了头条文章"):
            url = selector.xpath("//a/@data-url")
            if url and url[0].startswith("http://t.cn"):
                article_url = url[0]
        return article_url

    def get_topics(self, selector):
        """获取参与的微博话题"""
        span_list = selector.xpath("//span[@class='surl-text']")
        topics = ""
        topic_list = []
        for span in span_list:
            text = span.xpath("string(.)")
            if len(text) > 2 and text[0] == "#" and text[-1] == "#":
                topic_list.append(text[1:-1])
        if topic_list:
            topics = ",".join(topic_list)
        return topics

    def get_at_users(self, selector):
        """获取@用户"""
        a_list = selector.xpath("//a")
        at_users = ""
        at_list = []
        for a in a_list:
            if "@" + a.xpath("@href")[0][3:] == a.xpath("string(.)"):
                at_list.append(a.xpath("string(.)")[1:])
        if at_list:
            at_users = ",".join(at_list)
        return at_users

    def string_to_int(self, string):
        """字符串转换为整数"""
        if isinstance(string, int):
            return string
        elif string.endswith("万+"):
            string = string[:-2] + "0000"
        elif string.endswith("万"):
            string = float(string[:-1]) * 10000
        elif string.endswith("亿"):
            string = float(string[:-1]) * 100000000
        return int(string)

    def standardize_date(self, created_at):
        """标准化微博发布时间"""
        if "刚刚" in created_at:
            ts = datetime.now()
        elif "分钟" in created_at:
            minute = created_at[: created_at.find("分钟")]
            minute = timedelta(minutes=int(minute))
            ts = datetime.now() - minute
        elif "小时" in created_at:
            hour = created_at[: created_at.find("小时")]
            hour = timedelta(hours=int(hour))
            ts = datetime.now() - hour
        elif "昨天" in created_at:
            day = timedelta(days=1)
            ts = datetime.now() - day
        else:
            created_at = created_at.replace("+0800 ", "")
            ts = datetime.strptime(created_at, "%c")

        created_at = ts.strftime(DTFORMAT)
        full_created_at = ts.strftime("%Y-%m-%d %H:%M:%S")
        return created_at, full_created_at

    def standardize_info(self, weibo):
        """标准化信息，去除乱码"""
        for k, v in weibo.items():
            if (
                "bool" not in str(type(v))
                and "int" not in str(type(v))
                and "list" not in str(type(v))
                and "long" not in str(type(v))
            ):
                weibo[k] = (
                    v.replace("\u200b", "")
                    .encode(sys.stdout.encoding, "ignore")
                    .decode(sys.stdout.encoding)
                )
        return weibo

    def parse_weibo(self, weibo_info):
        weibo = OrderedDict()
        if weibo_info["user"]:
            weibo["user_id"] = weibo_info["user"]["id"]
            weibo["screen_name"] = weibo_info["user"]["screen_name"]
        else:
            weibo["user_id"] = ""
            weibo["screen_name"] = ""
        weibo["id"] = int(weibo_info["id"])
        weibo["bid"] = weibo_info["bid"]
        text_body = weibo_info["text"]
        selector = etree.HTML(f"{text_body}<hr>" if text_body.isspace() else text_body)
        if self.remove_html_tag:
            text_list = selector.xpath("//text()")
            # 若text_list中的某个字符串元素以 @ 或 # 开始，则将该元素与前后元素合并为新元素，否则会带来没有必要的换行
            text_list_modified = []
            for ele in range(len(text_list)):
                if ele > 0 and (text_list[ele-1].startswith(('@','#')) or text_list[ele].startswith(('@','#'))):
                    text_list_modified[-1] += text_list[ele]
                else:
                    text_list_modified.append(text_list[ele])
            weibo["text"] = "\n".join(text_list_modified)
        else:
            weibo["text"] = text_body
        weibo["article_url"] = self.get_article_url(selector)
        weibo["pics"] = self.get_pics(weibo_info)
        weibo["video_url"] = self.get_video_url(weibo_info)  # 普通视频URL
        weibo["live_photo_url"] = self.get_live_photo_url(weibo_info)  # Live Photo视频URL
        weibo["location"] = self.get_location(selector)
        weibo["created_at"] = weibo_info["created_at"]
        weibo["source"] = weibo_info["source"]
        weibo["attitudes_count"] = self.string_to_int(
            weibo_info.get("attitudes_count", 0)
        )
        weibo["comments_count"] = self.string_to_int(
            weibo_info.get("comments_count", 0)
        )
        weibo["reposts_count"] = self.string_to_int(weibo_info.get("reposts_count", 0))
        weibo["topics"] = self.get_topics(selector)
        weibo["at_users"] = self.get_at_users(selector)
        
        # 使用 LLM 分析微博内容
        if self.llm_analyzer:
            weibo = self.llm_analyzer.analyze_weibo(weibo)
            logger.info("完整分析结果：\n%s", json.dumps(weibo, ensure_ascii=False, indent=2))
        return self.standardize_info(weibo)

    def print_user_info(self):
        """打印用户信息"""
        logger.info("+" * 100)
        logger.info("用户信息")
        logger.info("用户id：%s", self.user["id"])
        logger.info("用户昵称：%s", self.user["screen_name"])
        gender = "女" if self.user["gender"] == "f" else "男"
        logger.info("性别：%s", gender)
        logger.info("生日：%s", self.user["birthday"])
        logger.info("所在地：%s", self.user["location"])
        logger.info("教育经历：%s", self.user["education"])
        logger.info("公司：%s", self.user["company"])
        logger.info("阳光信用：%s", self.user["sunshine"])
        logger.info("注册时间：%s", self.user["registration_time"])
        logger.info("微博数：%d", self.user["statuses_count"])
        logger.info("粉丝数：%d", self.user["followers_count"])
        logger.info("关注数：%d", self.user["follow_count"])
        logger.info("url：https://m.weibo.cn/profile/%s", self.user["id"])
        if self.user.get("verified_reason"):
            logger.info(self.user["verified_reason"])
        logger.info(self.user["description"])
        logger.info("+" * 100)

    def print_one_weibo(self, weibo):
        """打印一条微博"""
        try:
            logger.info("微博id：%d", weibo["id"])
            logger.info("微博正文：%s", weibo["text"])
            logger.info("原始图片url：%s", weibo["pics"])
            logger.info("微博位置：%s", weibo["location"])
            logger.info("发布时间：%s", weibo["created_at"])
            logger.info("发布工具：%s", weibo["source"])
            logger.info("点赞数：%d", weibo["attitudes_count"])
            logger.info("评论数：%d", weibo["comments_count"])
            logger.info("转发数：%d", weibo["reposts_count"])
            logger.info("话题：%s", weibo["topics"])
            logger.info("@用户：%s", weibo["at_users"])
            logger.info("url：https://m.weibo.cn/detail/%d", weibo["id"])
        except OSError:
            pass

    def print_weibo(self, weibo):
        """打印微博，若为转发微博，会同时打印原创和转发部分"""
        if weibo.get("retweet"):
            logger.info("*" * 100)
            logger.info("转发部分：")
            self.print_one_weibo(weibo["retweet"])
            logger.info("*" * 100)
            logger.info("原创部分：")
        self.print_one_weibo(weibo)
        logger.info("-" * 120)

    def get_one_weibo(self, info):
        """获取一条微博的全部信息"""
        try:
            weibo_info = info["mblog"]
            weibo_id = weibo_info["id"]
            retweeted_status = weibo_info.get("retweeted_status")
            is_long = (
                True if weibo_info.get("pic_num") > 9 else weibo_info.get("isLongText")
            )
            if retweeted_status and retweeted_status.get("id"):  # 转发
                retweet_id = retweeted_status.get("id")
                is_long_retweet = retweeted_status.get("isLongText")
                if is_long:
                    weibo = self.get_long_weibo(weibo_id)
                    if not weibo:
                        weibo = self.parse_weibo(weibo_info)
                else:
                    weibo = self.parse_weibo(weibo_info)
                if is_long_retweet:
                    retweet = self.get_long_weibo(retweet_id)
                    if not retweet:
                        retweet = self.parse_weibo(retweeted_status)
                else:
                    retweet = self.parse_weibo(retweeted_status)
                (
                    retweet["created_at"],
                    retweet["full_created_at"],
                ) = self.standardize_date(retweeted_status["created_at"])
                weibo["retweet"] = retweet
            else:  # 原创
                if is_long:
                    weibo = self.get_long_weibo(weibo_id)
                    if not weibo:
                        weibo = self.parse_weibo(weibo_info)
                else:
                    weibo = self.parse_weibo(weibo_info)
            weibo["created_at"], weibo["full_created_at"] = self.standardize_date(
                weibo_info["created_at"]
            )
            return weibo
        except Exception as e:
            logger.error(f"获取一页的微博失败, page: {page}")
            logger.exception(e)
            
            # 添加错误恢复机制
            error_delay = random.uniform(2, 5)
            logger.info(f"页面获取失败后延迟 {error_delay:.2f} 秒")
            sleep(error_delay)
            
            # 检查是否为432错误（频繁请求被限制）
            if "432" in str(e):
                logger.warning(f"遇到432错误，触发恢复措施")
                
                # 切换User-Agent
                if hasattr(self, 'headers') and 'User-Agent' in self.headers:
                    if hasattr(self, 'user_agent_list') and self.user_agent_list:
                        self.headers['User-Agent'] = random.choice(self.user_agent_list)
                        logger.info(f"已切换User-Agent")
                
                # 切换代理
                if hasattr(self, 'get_next_proxy'):
                    self.get_next_proxy()
            
            return []

    def get_weibo_comments(self, weibo, max_count, on_downloaded):
        """
        :weibo standardlized weibo
        :max_count 最大允许下载数
        :on_downloaded 下载完成时的实例方法回调
        """
        if weibo["comments_count"] == 0:
            return

        logger.info(
            "正在下载评论 微博id:{id}".format(id=weibo["id"])
        )
        self._get_weibo_comments_cookie(weibo, 0, max_count, None, on_downloaded)

    def get_weibo_reposts(self, weibo, max_count, on_downloaded):
        """
        :weibo standardlized weibo
        :max_count 最大允许下载数
        :on_downloaded 下载完成时的实例方法回调
        """
        if weibo["reposts_count"] == 0:
            return

        logger.info(
            "正在下载转发 微博id:{id}".format(id=weibo["id"])
        )
        self._get_weibo_reposts_cookie(weibo, 0, max_count, 1, on_downloaded)

    def _get_weibo_comments_cookie(
        self, weibo, cur_count, max_count, max_id, on_downloaded
    ):
        """
        :weibo standardlized weibo
        :cur_count  已经下载的评论数
        :max_count 最大允许下载数
        :max_id 微博返回的max_id参数
        :on_downloaded 下载完成时的实例方法回调
        """
        if cur_count >= max_count:
            return

        id = weibo["id"]
        params = {"mid": id}
        if max_id:
            params["max_id"] = max_id
        url = "https://m.weibo.cn/comments/hotflow?max_id_type=0"
        req = self.session.get(
            url,
            params=params,
            headers=self.headers,
        )
        json = None
        error = False
        try:
            json = req.json()
        except Exception as e:
            # 没有cookie会抓取失败
            # 微博日期小于某个日期的用这个url会被403 需要用老办法尝试一下
            error = True

        if error:
            # 最大好像只能有50条 TODO: improvement
            self._get_weibo_comments_nocookie(weibo, 0, max_count, 1, on_downloaded)
            return

        data = json.get("data")
        if not data:
            # 新接口没有抓取到的老接口也试一下
            self._get_weibo_comments_nocookie(weibo, 0, max_count, 1, on_downloaded)
            return

        comments = data.get("data")
        count = len(comments)
        if count == 0:
            # 没有了可以直接跳出递归
            return

        if on_downloaded:
            on_downloaded(weibo, comments)

        # 随机睡眠一下
        if max_count % 40 == 0:
            sleep(random.randint(1, 5))

        cur_count += count
        max_id = data.get("max_id")

        if max_id == 0:
            return

        self._get_weibo_comments_cookie(
            weibo, cur_count, max_count, max_id, on_downloaded
        )

    def _get_weibo_comments_nocookie(
        self, weibo, cur_count, max_count, page, on_downloaded
    ):
        """
        :weibo standardlized weibo
        :cur_count  已经下载的评论数
        :max_count 最大允许下载数
        :page 下载的页码 从 1 开始
        :on_downloaded 下载完成时的实例方法回调
        """
        if cur_count >= max_count:
            return
        id = weibo["id"]
        url = "https://m.weibo.cn/api/comments/show?id={id}&page={page}".format(
            id=id, page=page
        )
        req = self.session.get(url)
        json = None
        try:
            json = req.json()
        except Exception as e:
            logger.warning("未能抓取完整评论 微博id: {id}".format(id=id))
            return

        data = json.get("data")
        if not data:
            return
        comments = data.get("data")
        count = len(comments)
        if count == 0:
            # 没有了可以直接跳出递归
            return

        if on_downloaded:
            on_downloaded(weibo, comments)

        cur_count += count
        page += 1

        # 随机睡眠一下
        if page % 2 == 0:
            sleep(random.randint(1, 5))

        req_page = data.get("max")

        if req_page == 0:
            return

        if page > req_page:
            return
        self._get_weibo_comments_nocookie(
            weibo, cur_count, max_count, page, on_downloaded
        )

    def _get_weibo_reposts_cookie(
        self, weibo, cur_count, max_count, page, on_downloaded
    ):
        """
        :weibo standardlized weibo
        :cur_count  已经下载的转发数
        :max_count 最大允许下载数
        :page 下载的页码 从 1 开始
        :on_downloaded 下载完成时的实例方法回调
        """
        if cur_count >= max_count:
            return
        id = weibo["id"]
        url = "https://m.weibo.cn/api/statuses/repostTimeline"
        params = {"id": id, "page": page}
        req = self.session.get(
            url,
            params=params,
            headers=self.headers,
        )

        json = None
        try:
            json = req.json()
        except Exception as e:
            logger.warning(
                "未能抓取完整转发 微博id: {id}".format(id=id)
            )
            return

        data = json.get("data")
        if not data:
            return
        reposts = data.get("data")
        count = len(reposts)
        if count == 0:
            # 没有了可以直接跳出递归
            return

        if on_downloaded:
            on_downloaded(weibo, reposts)

        cur_count += count
        page += 1

        # 随机睡眠一下
        if page % 2 == 0:
            sleep(random.randint(2, 5))

        req_page = data.get("max")

        if req_page == 0:
            return

        if page > req_page:
            return
        self._get_weibo_reposts_cookie(weibo, cur_count, max_count, page, on_downloaded)

    def is_pinned_weibo(self, info):
        """判断微博是否为置顶微博"""
        isTop=False
        # Only works for sim chinese
        if "mblog" in info and "title" in info["mblog"] and "text" in info["mblog"]["title"] and info["mblog"]["title"]["text"]=="置顶":
            isTop=True
        return isTop
    

    def get_one_page(self, page):
        """获取一页的全部微博"""
        try:
            # 页面请求前随机延迟，避免请求过于规律
            page_delay = random.uniform(0.5, 2.0)
            logger.debug(f"页面 {page} 请求前随机延迟 {page_delay:.2f} 秒")
            sleep(page_delay)
            
            js = self.get_weibo_json(page)
            
            # 检查返回数据的有效性
            if not isinstance(js, dict) or "ok" not in js:
                logger.error(f"页面 {page} 返回数据格式错误: {str(js)}")
                return []
                
            if js["ok"]:
                # 检查data和cards字段是否存在
                if "data" not in js or "cards" not in js["data"]:
                    logger.warning(f"页面 {page} 数据结构不完整")
                    return []
                    
                weibos = js["data"]["cards"]
                
                if self.query:
                    weibos = weibos[0]["card_group"]
                # 如果需要检查cookie，在循环第一个人的时候，就要看看仅自己可见的信息有没有，要是没有直接报错
                for w in weibos:
                    if w["card_type"] == 11:
                        temp = w.get("card_group",[0])
                        if len(temp) >= 1:
                            w = temp[0] or w
                        else:
                            w = w
                    if w["card_type"] == 9:
                        wb = self.get_one_weibo(w)
                        if wb:
                            if (
                                const.CHECK_COOKIE["CHECK"]
                                and (not const.CHECK_COOKIE["CHECKED"])
                                and wb["text"].startswith(
                                    const.CHECK_COOKIE["HIDDEN_WEIBO"]
                                )
                            ):
                                const.CHECK_COOKIE["CHECKED"] = True
                                logger.info("cookie检查通过")
                                if const.CHECK_COOKIE["EXIT_AFTER_CHECK"]:
                                    return True
                            # 检查微博ID是否已存在
                            if wb["id"] in self.weibo_id_list:
                                logger.debug(f"微博 {wb['id']} 已存在，跳过")
                                continue
                                
                            # 检查微博发布时间
                            try:
                                created_at = datetime.strptime(wb["created_at"], DTFORMAT)
                                since_date = datetime.strptime(
                                    self.user_config["since_date"], DTFORMAT
                                )
                            except ValueError as e:
                                logger.error(f"日期格式解析错误: {str(e)}")
                                logger.error(f"问题数据: {wb['created_at']}")
                                continue
                            if const.MODE == "append":
                                # append模式下不会对置顶微博做任何处理

                                # 由于微博本身的调整，下面判断是否为置顶的代码已失效，默认所有用户第一条均为置顶
                                if self.is_pinned_weibo(w):
                                    continue
                                if const.CHECK_COOKIE["GUESS_PIN"]:
                                    const.CHECK_COOKIE["GUESS_PIN"] = False
                                    continue

                                if self.first_crawler:
                                    # 置顶微博的具体时间不好判定，将非置顶微博当成最新微博，写入上次抓取id的csv
                                    self.latest_weibo_id = str(wb["id"])
                                    csvutil.update_last_weibo_id(
                                        wb["user_id"],
                                        str(wb["id"]) + " " + wb["created_at"],
                                        self.user_csv_file_path,
                                    )
                                    self.first_crawler = False
                                if str(wb["id"]) == self.last_weibo_id:
                                    if const.CHECK_COOKIE["CHECK"] and (
                                        not const.CHECK_COOKIE["CHECKED"]
                                    ):
                                        # 已经爬取过最新的了，只是没检查到cookie，一旦检查通过，直接放行
                                        const.CHECK_COOKIE["EXIT_AFTER_CHECK"] = True
                                        continue
                                    if self.last_weibo_id == self.latest_weibo_id:
                                        logger.info(
                                            "{} 用户没有发新微博".format(
                                                self.user["screen_name"]
                                            )
                                        )
                                    else:
                                        logger.info(
                                            "增量获取微博完毕，将最新微博id从 {} 变更为 {}".format(
                                                self.last_weibo_id, self.latest_weibo_id
                                            )
                                        )
                                    return True
                                # 上一次标记的微博被删了，就把上一条微博时间记录推前两天，多抓点评论或者微博内容修改
                                # TODO 更加合理的流程是，即使读取到上次更新微博id，也抓取增量评论，由此获得更多的评论
                                since_date = datetime.strptime(
                                    convert_to_days_ago(self.last_weibo_date, 1),
                                    DTFORMAT,
                                )
                            if created_at < since_date:
                                if self.is_pinned_weibo(w):
                                    continue
                                # 如果要检查还没有检查cookie，不能直接跳出
                                elif const.CHECK_COOKIE["CHECK"] and (
                                    not const.CHECK_COOKIE["CHECKED"]
                                ):
                                    continue
                                else:
                                    logger.info(
                                        "{}已获取{}({})的第{}页{}微博{}".format(
                                            "-" * 30,
                                            self.user["screen_name"],
                                            self.user["id"],
                                            page,
                                            '包含"' + self.query + '"的'
                                            if self.query
                                            else "",
                                            "-" * 30,
                                        )
                                    )
                                    return True
                            if (not self.only_crawl_original) or ("retweet" not in wb.keys()):
                                self.weibo.append(wb)
                                self.weibo_id_list.append(wb["id"])
                                self.got_count += 1
                                # 这里是系统日志输出，尽量别太杂
                                logger.info(
                                    "已获取用户 {} 的微博，内容为 {}".format(
                                        self.user["screen_name"], wb["text"]
                                    )
                                )
                                # self.print_weibo(wb)
                            else:
                                logger.info("正在过滤转发微博")
                    
                if const.CHECK_COOKIE["CHECK"] and not const.CHECK_COOKIE["CHECKED"]:
                    logger.warning("经检查，cookie无效，系统退出")
                    if const.NOTIFY["NOTIFY"]:
                        push_deer("经检查，cookie无效，系统退出")
                    sys.exit()
            else:
                return True
            logger.info(
                "{}已获取{}({})的第{}页微博{}".format(
                    "-" * 30, self.user["screen_name"], self.user["id"], page, "-" * 30
                )
            )
        except Exception as e:
            logger.exception(e)

    def get_page_count(self):
        """获取微博页数"""
        try:
            weibo_count = self.user["statuses_count"]
            page_weibo_count = self.page_weibo_count
            page_count = int(math.ceil(weibo_count / page_weibo_count))
            if not isinstance(page_weibo_count, int):
                raise ValueError("config.json中每页爬取的微博数 page_weibo_count 必须是一个整数")
            return page_count
        except KeyError:
            logger.exception(
                "程序出错，错误原因可能为以下两者：\n"
                "1.user_id不正确；\n"
                "2.此用户微博可能需要设置cookie才能爬取。\n"
                "解决方案：\n"
                "请参考\n"
                "https://github.com/dataabc/weibo-crawler#如何获取user_id\n"
                "获取正确的user_id；\n"
                "或者参考\n"
                "https://github.com/dataabc/weibo-crawler#3程序设置\n"
                "中的“设置cookie”部分设置cookie信息"
            )

    def get_write_info(self, wrote_count):
        """获取要写入的微博信息"""
        write_info = []
        for w in self.weibo[wrote_count:]:
            wb = OrderedDict()
            for k, v in w.items():
                if k not in ["user_id", "screen_name", "retweet"]:
                    if "unicode" in str(type(v)):
                        v = v.encode("utf-8")
                    if k == "id":
                        v = str(v) + "\t"
                    wb[k] = v
            if not self.only_crawl_original:
                if w.get("retweet"):
                    wb["is_original"] = False
                    for k2, v2 in w["retweet"].items():
                        if "unicode" in str(type(v2)):
                            v2 = v2.encode("utf-8")
                        if k2 == "id":
                            v2 = str(v2) + "\t"
                        wb["retweet_" + k2] = v2
                else:
                    wb["is_original"] = True
            write_info.append(wb)
        return write_info

    def get_filepath(self, type):
        """获取结果文件路径"""
        try:
            dir_name = self.user["screen_name"]
            if self.user_id_as_folder_name:
                dir_name = str(self.user_config["user_id"])
            file_dir = (
                os.path.split(os.path.realpath(__file__))[0]
                + os.sep
                + "weibo"
                + os.sep
                + dir_name
            )
            if type in ["img", "video", "live_photo"]:
                file_dir = file_dir + os.sep + type
            if not os.path.isdir(file_dir):
                os.makedirs(file_dir)
            if type in ["img", "video", "live_photo"]:
                return file_dir
            file_path = file_dir + os.sep + str(self.user_config["user_id"]) + "." + type
            return file_path
        except Exception as e:
            logger.exception(e)

    def get_result_headers(self):
        """获取要写入结果文件的表头"""
        result_headers = [
            "id",
            "bid",
            "正文",
            "头条文章url",
            "原始图片url",
            "视频url",
            "位置",
            "日期",
            "工具",
            "点赞数",
            "评论数",
            "转发数",
            "话题",
            "@用户",
            "完整日期",
        ]
        if not self.only_crawl_original:
            result_headers2 = ["是否原创", "源用户id", "源用户昵称"]
            result_headers3 = ["源微博" + r for r in result_headers]
            result_headers = result_headers + result_headers2 + result_headers3
        return result_headers

    def write_csv(self, wrote_count):
        """将爬到的信息写入csv文件"""
        write_info = self.get_write_info(wrote_count)
        result_headers = self.get_result_headers()
        result_data = [w.values() for w in write_info]
        file_path = self.get_filepath("csv")
        self.csv_helper(result_headers, result_data, file_path)

    def csv_helper(self, headers, result_data, file_path):
        """将指定信息写入csv文件"""
        if not os.path.isfile(file_path):
            is_first_write = 1
        else:
            is_first_write = 0
        if sys.version < "3":  # python2.x
            with open(file_path, "ab") as f:
                f.write(codecs.BOM_UTF8)
                writer = csv.writer(f)
                if is_first_write:
                    writer.writerows([headers])
                writer.writerows(result_data)
        else:  # python3.x

            with open(file_path, "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                if is_first_write:
                    writer.writerows([headers])
                writer.writerows(result_data)
        if headers[0] == "id":
            logger.info("%d条微博写入csv文件完毕,保存路径:", self.got_count)
        else:
            logger.info("%s 信息写入csv文件完毕，保存路径:", self.user["screen_name"])
        logger.info(file_path)

    def update_json_data(self, data, weibo_info):
        """更新要写入json结果文件中的数据，已经存在于json中的信息更新为最新值，不存在的信息添加到data中"""
        data["user"] = self.user
        if data.get("weibo"):
            is_new = 1  # 待写入微博是否全部为新微博，即待写入微博与json中的数据不重复
            for old in data["weibo"]:
                if weibo_info[-1]["id"] == old["id"]:
                    is_new = 0
                    break
            if is_new == 0:
                for new in weibo_info:
                    flag = 1
                    for i, old in enumerate(data["weibo"]):
                        if new["id"] == old["id"]:
                            data["weibo"][i] = new
                            flag = 0
                            break
                    if flag:
                        data["weibo"].append(new)
            else:
                data["weibo"] += weibo_info
        else:
            data["weibo"] = weibo_info
        return data

    def write_json(self, wrote_count):
        """将爬到的信息写入json文件"""
        data = {}
        path = self.get_filepath("json")
        if os.path.isfile(path):
            with codecs.open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        weibo_info = self.weibo[wrote_count:]
        data = self.update_json_data(data, weibo_info)
        with codecs.open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logger.info("%d条微博写入json文件完毕,保存路径:", self.got_count)
        logger.info(path)

    def send_post_request_with_token(self, url, data, token, max_retries, backoff_factor):
        headers = {
            'Content-Type': 'application/json',
            'api-token': f'{token}',
        }
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, json=data, headers=headers)
                if response.status_code == requests.codes.ok:
                    return response.json()
                else:
                    raise RequestException(f"Unexpected response status: {response.status_code}")
            except RequestException as e:
                if attempt < max_retries:
                    sleep(backoff_factor * (attempt + 1))  # 逐步增加等待时间，避免频繁重试
                    continue
                else:
                    logger.error(f"在尝试{max_retries}次发出POST连接后，请求失败：{e}")

    def write_post(self, wrote_count):
        """将爬到的信息通过POST发出"""
        data = {}
        data['user'] = self.user
        weibo_info = self.weibo[wrote_count:]
        if data.get('weibo'):
            data['weibo'] += weibo_info
        else:
            data['weibo'] = weibo_info

        if data:
            self.send_post_request_with_token(self.post_config["api_url"], data, self.post_config["api_token"], 3, 2)
            logger.info(u'%d条微博通过POST发送到 %s', len(data['weibo']), self.post_config["api_url"])
        else:
            logger.info(u'没有获取到微博，略过API POST')


    def info_to_mongodb(self, collection, info_list):
        """将爬取的信息写入MongoDB数据库"""
        try:
            import pymongo
        except ImportError:
            logger.warning("系统中可能没有安装pymongo库，请先运行 pip install pymongo ，再运行程序")
            sys.exit()
        try:
            from pymongo import MongoClient

            client = MongoClient(self.mongodb_URI)
            db = client["weibo"]
            collection = db[collection]
            if len(self.write_mode) > 1:
                new_info_list = copy.deepcopy(info_list)
            else:
                new_info_list = info_list
            for info in new_info_list:
                if not collection.find_one({"id": info["id"]}):
                    collection.insert_one(info)
                else:
                    collection.update_one({"id": info["id"]}, {"$set": info})
        except pymongo.errors.ServerSelectionTimeoutError:
            logger.warning("系统中可能没有安装或启动MongoDB数据库，请先根据系统环境安装或启动MongoDB，再运行程序")
            sys.exit()

    def weibo_to_mongodb(self, wrote_count):
        """将爬取的微博信息写入MongoDB数据库"""
        self.info_to_mongodb("weibo", self.weibo[wrote_count:])
        logger.info("%d条微博写入MongoDB数据库完毕", self.got_count)

    def mysql_create(self, connection, sql):
        """创建MySQL数据库或表"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
        finally:
            connection.close()

    def mysql_create_database(self, mysql_config, sql):
        """创建MySQL数据库"""
        try:
            import pymysql
        except ImportError:
            logger.warning("系统中可能没有安装pymysql库，请先运行 pip install pymysql ，再运行程序")
            sys.exit()
        try:
            if self.mysql_config:
                mysql_config = self.mysql_config
            connection = pymysql.connect(**mysql_config)
            self.mysql_create(connection, sql)
        except pymysql.OperationalError:
            logger.warning("系统中可能没有安装或正确配置MySQL数据库，请先根据系统环境安装或配置MySQL，再运行程序")
            sys.exit()

    def mysql_create_table(self, mysql_config, sql):
        """创建MySQL表"""
        import pymysql

        if self.mysql_config:
            mysql_config = self.mysql_config
        mysql_config["db"] = "weibo"
        connection = pymysql.connect(**mysql_config)
        self.mysql_create(connection, sql)

    def mysql_insert(self, mysql_config, table, data_list):
        """
        向MySQL表插入或更新数据

        Parameters
        ----------
        mysql_config: map
            MySQL配置表
        table: str
            要插入的表名
        data_list: list
            要插入的数据列表

        Returns
        -------
        bool: SQL执行结果
        """
        import pymysql

        if len(data_list) > 0:
            keys = ", ".join(data_list[0].keys())
            values = ", ".join(["%s"] * len(data_list[0]))
            if self.mysql_config:
                mysql_config = self.mysql_config
            mysql_config["db"] = "weibo"
            connection = pymysql.connect(**mysql_config)
            cursor = connection.cursor()
            sql = """INSERT INTO {table}({keys}) VALUES ({values}) ON
                     DUPLICATE KEY UPDATE""".format(
                table=table, keys=keys, values=values
            )
            update = ",".join(
                [" {key} = values({key})".format(key=key) for key in data_list[0]]
            )
            sql += update
            try:
                cursor.executemany(sql, [tuple(data.values()) for data in data_list])
                connection.commit()
            except Exception as e:
                connection.rollback()
                logger.exception(e)
            finally:
                connection.close()

    def weibo_to_mysql(self, wrote_count):
        """将爬取的微博信息写入MySQL数据库"""
        # 使用实例中的mysql_config配置
        mysql_config = self.mysql_config if self.mysql_config else {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "123456",
            "charset": "utf8mb4",
        }
        # 创建'weibo'表
        create_table = """
                CREATE TABLE IF NOT EXISTS weibo (
                id varchar(20) NOT NULL,
                bid varchar(12) NOT NULL,
                user_id varchar(20),
                screen_name varchar(30),
                text text,
                article_url varchar(100),
                topics varchar(200),
                at_users varchar(1000),
                pics varchar(3000),
                video_url varchar(1000),
                live_photo_url varchar(1000),
                location varchar(100),
                created_at DATETIME,
                source varchar(30),
                attitudes_count INT,
                comments_count INT,
                reposts_count INT,
                retweet_id varchar(20),
                PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        self.mysql_create_table(mysql_config, create_table)

        # 要插入的微博列表
        weibo_list = []
        # 要插入的转发微博列表
        retweet_list = []
        if len(self.write_mode) > 1:
            info_list = copy.deepcopy(self.weibo[wrote_count:])
        else:
            info_list = self.weibo[wrote_count:]
        for w in info_list:
            w["created_at"] = w["full_created_at"]
            del w["full_created_at"]

            if "retweet" in w:
                r = w["retweet"]
                r["retweet_id"] = ""
                r["created_at"] = r["full_created_at"]
                del r["full_created_at"]
                retweet_list.append(r)
                w["retweet_id"] = r["id"]
                del w["retweet"]
            else:
                w["retweet_id"] = ""
            weibo_list.append(w)
        # 在'weibo'表中插入或更新微博数据
        self.mysql_insert(mysql_config, "weibo", retweet_list)
        self.mysql_insert(mysql_config, "weibo", weibo_list)
        logger.info("%d条微博写入MySQL数据库完毕", self.got_count)

    def weibo_to_sqlite(self, wrote_count):
        con = self.get_sqlite_connection()
        weibo_list = []
        retweet_list = []
        info_list = copy.deepcopy(self.weibo[wrote_count:])
        for w in info_list:
            if "retweet" in w:
                w["retweet"]["retweet_id"] = ""
                retweet_list.append(w["retweet"])
                w["retweet_id"] = w["retweet"]["id"]
                del w["retweet"]
            else:
                w["retweet_id"] = ""
            weibo_list.append(w)

        comment_max_count = self.comment_max_download_count
        repost_max_count = self.comment_max_download_count
        download_comment = self.download_comment and comment_max_count > 0
        download_repost = self.download_repost and repost_max_count > 0

        count = 0
        for weibo in weibo_list:
            self.sqlite_insert_weibo(con, weibo)
            if (download_comment) and (weibo["comments_count"] > 0):
                self.get_weibo_comments(
                    weibo, comment_max_count, self.sqlite_insert_comments
                )
                count += 1
                if count % 20:
                    sleep(random.randint(3, 6))
            if (download_repost) and (weibo["reposts_count"] > 0):
                self.get_weibo_reposts(
                    weibo, repost_max_count, self.sqlite_insert_reposts
                )
                count += 1
                if count % 20:
                    sleep(random.randint(3, 6))

        for weibo in retweet_list:
            self.sqlite_insert_weibo(con, weibo)
        con.close()

    def sqlite_insert_comments(self, weibo, comments):
        if not comments or len(comments) == 0:
            return
        con = self.get_sqlite_connection()
        for comment in comments:
            data = self.parse_sqlite_comment(comment, weibo)
            self.sqlite_insert(con, data, "comments")
            if "comments" in comment and isinstance(comment["comments"], list):
                for c in comment["comments"]:
                    data = self.parse_sqlite_comment(c, weibo)
                    self.sqlite_insert(con, data, "comments")
        con.close()

    def sqlite_insert_reposts(self, weibo, reposts):
        if not reposts or len(reposts) == 0:
            return
        con = self.get_sqlite_connection()
        for repost in reposts:
            data = self.parse_sqlite_repost(repost, weibo)
            self.sqlite_insert(con, data, "reposts")

        con.close()

    def parse_sqlite_comment(self, comment, weibo):
        if not comment:
            return
        sqlite_comment = OrderedDict()
        sqlite_comment["id"] = comment["id"]

        self._try_get_value("bid", "bid", sqlite_comment, comment)
        self._try_get_value("root_id", "rootid", sqlite_comment, comment)
        self._try_get_value("created_at", "created_at", sqlite_comment, comment)
        sqlite_comment["weibo_id"] = weibo["id"]

        sqlite_comment["user_id"] = comment["user"]["id"]
        sqlite_comment["user_screen_name"] = comment["user"]["screen_name"]
        self._try_get_value(
            "user_avatar_url", "avatar_hd", sqlite_comment, comment["user"]
        )
        if self.remove_html_tag:
            sqlite_comment["text"] = re.sub('<[^<]+?>', '', comment["text"]).replace('\n', '').strip()
        else:
            sqlite_comment["text"] = comment["text"]
        
        sqlite_comment["pic_url"] = ""
        if comment.get("pic"):
            sqlite_comment["pic_url"] = comment["pic"]["large"]["url"]
        if  sqlite_comment["pic_url"]:
            pic_url = sqlite_comment["pic_url"]
            pic_path = self.get_filepath("comment_img")
            if not os.path.exists(pic_path):
                os.makedirs(pic_path)
            pic_name = "{id}_{created_at}.jpg".format(
                id=sqlite_comment["id"], created_at=sqlite_comment["created_at"]
            )
            pic_full_path = os.path.join(pic_path, pic_name)
            if not os.path.exists(pic_full_path):
                try:
                    response = self.session.get(pic_url, timeout=10)
                    with open(pic_full_path, "wb") as f:
                        f.write(response.content)
                    logger.info("评论图片下载成功: %s", pic_full_path)
                except Exception as e:
                    logger.warning("下载评论图片失败: %s", e)
        self._try_get_value("like_count", "like_count", sqlite_comment, comment)
        return sqlite_comment

    def parse_sqlite_repost(self, repost, weibo):
        if not repost:
            return
        sqlite_repost = OrderedDict()
        sqlite_repost["id"] = repost["id"]

        self._try_get_value("bid", "bid", sqlite_repost, repost)
        self._try_get_value("created_at", "created_at", sqlite_repost, repost)
        sqlite_repost["weibo_id"] = weibo["id"]

        sqlite_repost["user_id"] = repost["user"]["id"]
        sqlite_repost["user_screen_name"] = repost["user"]["screen_name"]
        self._try_get_value(
            "user_avatar_url", "profile_image_url", sqlite_repost, repost["user"]
        )
        text = repost.get("raw_text")
        if text:
            text = text.split("//", 1)[0]
        if text is None or text == "" or text == "Repost":
            text = "转发微博"
        sqlite_repost["text"] = text
        self._try_get_value("like_count", "attitudes_count", sqlite_repost, repost)
        return sqlite_repost

    def _try_get_value(self, source_name, target_name, dict, json):
        dict[source_name] = ""
        value = json.get(target_name)
        if value:
            dict[source_name] = value

    def sqlite_insert_weibo(self, con: sqlite3.Connection, weibo: dict):
        sqlite_weibo = self.parse_sqlite_weibo(weibo)
        self.sqlite_insert(con, sqlite_weibo, "weibo")

    def parse_sqlite_weibo(self, weibo):
        if not weibo:
            return
        sqlite_weibo = OrderedDict()
        sqlite_weibo["user_id"] = weibo["user_id"]
        sqlite_weibo["id"] = weibo["id"]
        sqlite_weibo["bid"] = weibo["bid"]
        sqlite_weibo["screen_name"] = weibo["screen_name"]
        sqlite_weibo["text"] = weibo["text"]
        sqlite_weibo["article_url"] = weibo["article_url"]
        sqlite_weibo["topics"] = weibo["topics"]
        sqlite_weibo["pics"] = weibo["pics"]
        sqlite_weibo["video_url"] = weibo["video_url"]
        sqlite_weibo["live_photo_url"] = weibo["live_photo_url"]
        sqlite_weibo["location"] = weibo["location"]
        sqlite_weibo["created_at"] = weibo["full_created_at"]
        sqlite_weibo["source"] = weibo["source"]
        sqlite_weibo["attitudes_count"] = weibo["attitudes_count"]
        sqlite_weibo["comments_count"] = weibo["comments_count"]
        sqlite_weibo["reposts_count"] = weibo["reposts_count"]
        sqlite_weibo["retweet_id"] = weibo["retweet_id"]
        sqlite_weibo["at_users"] = weibo["at_users"]
        return sqlite_weibo

    def user_to_sqlite(self):
        con = self.get_sqlite_connection()
        self.sqlite_insert_user(con, self.user)
        con.close()

    def sqlite_insert_user(self, con: sqlite3.Connection, user: dict):
        sqlite_user = self.parse_sqlite_user(user)
        self.sqlite_insert(con, sqlite_user, "user")

    def parse_sqlite_user(self, user):
        if not user:
            return
        sqlite_user = OrderedDict()
        sqlite_user["id"] = user["id"]
        sqlite_user["nick_name"] = user["screen_name"]
        sqlite_user["gender"] = user["gender"]
        sqlite_user["follower_count"] = user["followers_count"]
        sqlite_user["follow_count"] = user["follow_count"]
        sqlite_user["birthday"] = user["birthday"]
        sqlite_user["location"] = user["location"]
        sqlite_user["edu"] = user["education"]
        sqlite_user["company"] = user["company"]
        sqlite_user["reg_date"] = user["registration_time"]
        sqlite_user["main_page_url"] = user["profile_url"]
        sqlite_user["avatar_url"] = user["avatar_hd"]
        sqlite_user["bio"] = user["description"]
        return sqlite_user

    def sqlite_insert(self, con: sqlite3.Connection, data: dict, table: str):
        if not data:
            return
        cur = con.cursor()
        keys = ",".join(data.keys())
        values = ",".join(["?"] * len(data))
        sql = """INSERT OR REPLACE INTO {table}({keys}) VALUES({values})
                """.format(
            table=table, keys=keys, values=values
        )
        cur.execute(sql, list(data.values()))
        con.commit()

    def get_sqlite_connection(self):
        path = self.get_sqlte_path()
        create = False
        if not os.path.exists(path):
            create = True

        con = sqlite3.connect(path)

        if create == True:
            self.create_sqlite_table(connection=con)

        return con

    def create_sqlite_table(self, connection: sqlite3.Connection):
        sql = self.get_sqlite_create_sql()
        cur = connection.cursor()
        cur.executescript(sql)
        connection.commit()

    def get_sqlte_path(self):
        return "./weibo/weibodata.db"

    def get_sqlite_create_sql(self):
        create_sql = """
                CREATE TABLE IF NOT EXISTS user (
                    id varchar(64) NOT NULL
                    ,nick_name varchar(64) NOT NULL
                    ,gender varchar(6)
                    ,follower_count integer
                    ,follow_count integer
                    ,birthday varchar(10)
                    ,location varchar(32)
                    ,edu varchar(32)
                    ,company varchar(32)
                    ,reg_date DATETIME
                    ,main_page_url text
                    ,avatar_url text
                    ,bio text
                    ,PRIMARY KEY (id)
                );

                CREATE TABLE IF NOT EXISTS weibo (
                    id varchar(20) NOT NULL
                    ,bid varchar(12) NOT NULL
                    ,user_id varchar(20)
                    ,screen_name varchar(30)
                    ,text varchar(2000)
                    ,article_url varchar(100)
                    ,topics varchar(200)
                    ,at_users varchar(1000)
                    ,pics varchar(3000)
                    ,video_url varchar(1000)
                    ,live_photo_url varchar(1000)
                    ,location varchar(100)
                    ,created_at DATETIME
                    ,source varchar(30)
                    ,attitudes_count INT
                    ,comments_count INT
                    ,reposts_count INT
                    ,retweet_id varchar(20)
                    ,PRIMARY KEY (id)
                );

                CREATE TABLE IF NOT EXISTS bins (
                    id integer PRIMARY KEY AUTOINCREMENT
                    ,ext varchar(10) NOT NULL /*file extension*/
                    ,data blob NOT NULL
                    ,weibo_id varchar(20)
                    ,comment_id varchar(20)
                    ,path text
                    ,url text
                );

                CREATE TABLE IF NOT EXISTS comments (
                    id varchar(20) NOT NULL
                    ,bid varchar(20) NOT NULL
                    ,weibo_id varchar(32) NOT NULL
                    ,root_id varchar(20) 
                    ,user_id varchar(20) NOT NULL
                    ,created_at varchar(20)
                    ,user_screen_name varchar(64) NOT NULL
                    ,user_avatar_url text
                    ,text varchar(1000)
                    ,pic_url text
                    ,like_count integer
                    ,PRIMARY KEY (id)
                );

                CREATE TABLE IF NOT EXISTS reposts (
                    id varchar(20) NOT NULL
                    ,bid varchar(20) NOT NULL
                    ,weibo_id varchar(32) NOT NULL
                    ,user_id varchar(20) NOT NULL
                    ,created_at varchar(20)
                    ,user_screen_name varchar(64) NOT NULL
                    ,user_avatar_url text
                    ,text varchar(1000)
                    ,like_count integer
                    ,PRIMARY KEY (id)
                );
                """
        return create_sql

    def update_user_config_file(self, user_config_file_path):
        """更新用户配置文件"""
        with open(user_config_file_path, "rb") as f:
            try:
                lines = f.read().splitlines()
                lines = [line.decode("utf-8-sig") for line in lines]
            except UnicodeDecodeError:
                logger.error("%s文件应为utf-8编码，请先将文件编码转为utf-8再运行程序", user_config_file_path)
                sys.exit()
            for i, line in enumerate(lines):
                info = line.split(" ")
                if len(info) > 0 and info[0].isdigit():
                    if self.user_config["user_id"] == info[0]:
                        if len(info) == 1:
                            info.append(self.user["screen_name"])
                            info.append(self.start_date)
                        if len(info) == 2:
                            info.append(self.start_date)
                        if len(info) > 2:
                            info[2] = self.start_date
                        lines[i] = " ".join(info)
                        break
        with codecs.open(user_config_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def write_data(self, wrote_count):
        """将爬到的信息写入文件或数据库"""
        # 使用print语句确保日志能显示在控制台
        print(f"=== 进入write_data函数: got_count={self.got_count}, wrote_count={wrote_count} ===")
        print(f"=== original_pic_download标志: {self.original_pic_download} (类型: {type(self.original_pic_download)}) ===")
        print(f"=== only_crawl_original标志: {self.only_crawl_original} (类型: {type(self.only_crawl_original)}) ===")
        print(f"=== 当前微博数据数量: {len(self.weibo)} ===")
        print(f"=== 需要处理的微博范围: {wrote_count} 到 {self.got_count} ===")
        logger.info(f"进入write_data函数: got_count={self.got_count}, wrote_count={wrote_count}")
        logger.info(f"original_pic_download标志: {self.original_pic_download} (类型: {type(self.original_pic_download)})")
        logger.info(f"only_crawl_original标志: {self.only_crawl_original} (类型: {type(self.only_crawl_original)})")
        logger.info(f"当前微博数据数量: {len(self.weibo)}")
        logger.info(f"需要处理的微博范围: {wrote_count} 到 {self.got_count}")
        
        # 即使没有新数据，也尝试下载文件，确保所有配置的下载操作都能执行
        try:
            # 写入数据到不同格式
            if self.got_count > wrote_count:
                # 在写入数据前添加随机延迟，避免请求过于规律
                delay = random.uniform(2, 5)
                print(f"=== 写入数据前随机延迟 {delay:.2f} 秒 ===")
                logger.info(f"写入数据前随机延迟 {delay:.2f} 秒")
                sleep(delay)
                
                if "csv" in self.write_mode:
                    print(f"=== 写入CSV文件 ===")
                    self.write_csv(wrote_count)
                if "json" in self.write_mode:
                    self.write_json(wrote_count)
                if "post" in self.write_mode:
                    self.write_post(wrote_count)
                if "mysql" in self.write_mode:
                    self.weibo_to_mysql(wrote_count)
                if "mongo" in self.write_mode:
                    self.weibo_to_mongodb(wrote_count)
                if "sqlite" in self.write_mode:
                    self.weibo_to_sqlite(wrote_count)
            else:
                print(f"=== 没有新数据需要写入: got_count <= wrote_count ===")
                logger.info("没有新数据需要写入: got_count <= wrote_count")
            
            # 下载原创微博文件
            print(f"=== 开始处理文件下载操作 ===")
            logger.info("开始处理文件下载操作")
            
            # 下载任务列表
            download_tasks = []
            if self.original_pic_download:
                download_tasks.append(("img", "original"))
                print(f"=== 添加原创微博图片下载任务 ===")
                logger.info("添加原创微博图片下载任务")
            else:
                print(f"=== 跳过原创微博图片下载任务，因为original_pic_download={self.original_pic_download} ===")
                logger.info(f"跳过原创微博图片下载任务，因为original_pic_download={self.original_pic_download}")
            
            if self.original_video_download:
                download_tasks.append(("video", "original"))
                print(f"=== 添加原创微博视频下载任务 ===")
                logger.info("添加原创微博视频下载任务")
            if self.original_live_photo_download:
                download_tasks.append(("live_photo", "original"))
                print(f"=== 添加原创微博Live Photo下载任务 ===")
                logger.info("添加原创微博Live Photo下载任务")
            
            # 如果不禁爬转发，添加转发微博下载任务
            if not self.only_crawl_original:
                print(f"=== 开始处理转发微博文件下载 ===")
                logger.info("开始处理转发微博文件下载")
                if self.retweet_pic_download:
                    download_tasks.append(("img", "retweet"))
                    print(f"=== 添加转发微博图片下载任务 ===")
                    logger.info("添加转发微博图片下载任务")
                if self.retweet_video_download:
                    download_tasks.append(("video", "retweet"))
                    print(f"=== 添加转发微博视频下载任务 ===")
                    logger.info("添加转发微博视频下载任务")
                if self.retweet_live_photo_download:
                    download_tasks.append(("live_photo", "retweet"))
                    print(f"=== 添加转发微博Live Photo下载任务 ===")
                    logger.info("添加转发微博Live Photo下载任务")
            
            # 打印最终下载任务列表
            print(f"=== 最终下载任务列表: {download_tasks} ===")
            logger.info(f"最终下载任务列表: {download_tasks}")
            
            # 智能处理下载任务，实现重试和代理切换
            max_retries = 3
            for task in download_tasks:
                file_type, weibo_type = task
                retry_count = 0
                success = False
                
                while retry_count < max_retries and not success:
                    try:
                        # 在每个下载任务前添加随机延迟
                        delay = random.uniform(3, 8)
                        print(f"=== 准备下载 {file_type} {weibo_type} 文件，随机延迟 {delay:.2f} 秒 ===")
                        logger.info(f"准备下载 {file_type} {weibo_type} 文件，随机延迟 {delay:.2f} 秒")
                        sleep(delay)
                        
                        # 如果之前遇到432错误，考虑切换代理
                        if hasattr(self, 'last_432_error') and self.last_432_error and retry_count > 0:
                            print(f"=== 检测到之前有432错误，尝试切换代理进行第 {retry_count+1} 次重试 ===")
                            logger.info(f"检测到之前有432错误，尝试切换代理进行第 {retry_count+1} 次重试")
                            if hasattr(self, 'get_next_proxy'):
                                self.get_next_proxy()
                        
                        # 执行下载
                        print(f"=== 执行下载 {file_type} {weibo_type} 文件 ===")
                        self.download_files(file_type, weibo_type, wrote_count)
                        success = True
                        print(f"=== 成功下载 {file_type} {weibo_type} 文件 ===")
                        logger.info(f"成功下载 {file_type} {weibo_type} 文件")
                        
                    except Exception as e:
                        retry_count += 1
                        error_msg = str(e)
                        print(f"=== 下载 {file_type} {weibo_type} 文件时出错: {error_msg}，第 {retry_count} 次重试 ===")
                        logger.error(f"下载 {file_type} {weibo_type} 文件时出错: {error_msg}，第 {retry_count} 次重试")
                        logger.exception(e)
                        
                        # 检查是否为432错误
                        if "432" in error_msg:
                            print(f"=== 检测到432错误，这可能是反爬机制导致的 ===")
                            logger.warning("检测到432错误，这可能是反爬机制导致的")
                            setattr(self, 'last_432_error', True)
                            # 432错误使用指数退避策略
                            backoff_time = min(30, 2 ** retry_count * 2)
                            print(f"=== 针对432错误，使用指数退避策略，等待 {backoff_time} 秒后重试 ===")
                            logger.info(f"针对432错误，使用指数退避策略，等待 {backoff_time} 秒后重试")
                            sleep(backoff_time)
                            # 切换User-Agent
                            if hasattr(self, 'user_agents') and self.user_agents:
                                new_agent = random.choice(self.user_agents)
                                self.headers['User-Agent'] = new_agent
                                print(f"=== 已切换User-Agent为: {new_agent} ===")
                                logger.info(f"已切换User-Agent为: {new_agent}")
                        else:
                            # 其他错误使用线性退避
                            sleep_time = random.uniform(2, 5)
                            print(f"=== 非432错误，等待 {sleep_time:.2f} 秒后重试 ===")
                            logger.info(f"非432错误，等待 {sleep_time:.2f} 秒后重试")
                            sleep(sleep_time)
                
                if not success:
                    print(f"=== 下载 {file_type} {weibo_type} 文件在 {max_retries} 次尝试后失败 ===")
                    logger.error(f"下载 {file_type} {weibo_type} 文件在 {max_retries} 次尝试后失败")
                    # 记录失败但继续处理其他任务
                    
            # 重置错误状态
            if hasattr(self, 'last_432_error'):
                self.last_432_error = False
                
        except Exception as e:
            print(f"=== write_data函数执行出错: {str(e)} ===")
            logger.error(f"write_data函数执行出错: {str(e)}")
            logger.exception(e)
            # 在异常发生后也添加随机延迟，避免立即重试导致的反爬
            sleep(random.uniform(5, 10))
        
        print(f"=== write_data函数执行完毕 ===")
        logger.info("write_data函数执行完毕")

    def get_pages(self):
        """获取全部微博"""
        try:
            # 初始化反爬相关变量
            consecutive_432_errors = 0
            max_consecutive_432 = 3
            page_retry_count = 0
            max_page_retries = 5
            
            # 添加初始随机延迟，模拟真实用户行为
            initial_delay = random.uniform(3, 8)
            logger.info(f"初始随机延迟 {initial_delay:.2f} 秒，模拟用户行为")
            sleep(initial_delay)
            
            # 用户id不可用
            if self.get_user_info() != 0:
                return
            
            logger.info("准备搜集 {} 的微博".format(self.user["screen_name"]))
            
            if const.MODE == "append" and (
                "first_crawler" not in self.__dict__ or self.first_crawler is False
            ):
                # 本次运行的某用户首次抓取，用于标记最新的微博id
                self.first_crawler = True
                const.CHECK_COOKIE["GUESS_PIN"] = True
            
            since_date = datetime.strptime(self.user_config["since_date"], DTFORMAT)
            today = datetime.today()
            
            if since_date <= today:    # since_date 若为未来则无需执行
                page_count = self.get_page_count()
                # 使用实际获取的页数进行爬取
                logger.info(f"计划爬取 {page_count} 页内容")
                wrote_count = 0
                page1 = 0
                random_pages = random.randint(1, 5)
                self.start_date = datetime.now().strftime(DTFORMAT)
                pages = range(self.start_page, page_count + 1)
                
                for page in tqdm(pages, desc="Progress"):
                    page_success = False
                    page_retry = 0
                    
                    # 对每个页面实现智能重试机制
                    while page_retry < max_page_retries and not page_success:
                        try:
                            # 检查连续432错误，超过阈值则采取更激进的措施
                            if consecutive_432_errors >= max_consecutive_432:
                                logger.warning(f"检测到连续 {consecutive_432_errors} 个432错误，采取紧急措施")
                                # 切换代理
                                if hasattr(self, 'get_next_proxy'):
                                    self.get_next_proxy()
                                # 切换User-Agent
                                if hasattr(self, 'user_agents') and self.user_agents:
                                    new_agent = random.choice(self.user_agents)
                                    self.headers['User-Agent'] = new_agent
                                    logger.info(f"已切换User-Agent为: {new_agent}")
                                # 延长等待时间
                                recovery_delay = random.uniform(15, 30)
                                logger.info(f"执行恢复策略，延长等待时间 {recovery_delay:.2f} 秒")
                                sleep(recovery_delay)
                                consecutive_432_errors = 0
                            
                            # 获取该页数据
                            is_end = self.get_one_page(page)
                            page_success = True
                            consecutive_432_errors = 0  # 重置连续错误计数
                            
                            # 确保每爬1页就调用write_data函数，不管is_end的值是什么
                            if page % 1 == 0:  # 每爬1页写入一次文件，方便测试
                                print(f"=== 调用write_data函数，page={page}，got_count={self.got_count}，wrote_count={wrote_count} ===")
                                self.write_data(wrote_count)
                                wrote_count = self.got_count
                                # 写入数据后也添加随机延迟
                                data_delay = random.uniform(2, 5)
                                logger.info(f"数据写入完成，随机延迟 {data_delay:.2f} 秒")
                                sleep(data_delay)
                            
                            if is_end:
                                break

                        except Exception as e:
                            page_retry += 1
                            error_msg = str(e)
                            logger.error(f"获取第 {page} 页微博时出错 (尝试 {page_retry}/{max_page_retries}): {error_msg}")
                            logger.exception(e)
                            
                            # 检查是否为432错误
                            if "432" in error_msg:
                                consecutive_432_errors += 1
                                logger.warning(f"检测到432错误，连续432错误计数: {consecutive_432_errors}")
                                # 432错误使用指数退避策略
                                backoff_time = min(60, 2 ** page_retry * 3)
                                logger.info(f"针对432错误，使用指数退避策略，等待 {backoff_time} 秒后重试")
                                # 切换User-Agent
                                if hasattr(self, 'user_agents') and self.user_agents:
                                    new_agent = random.choice(self.user_agents)
                                    self.headers['User-Agent'] = new_agent
                                    logger.info(f"已切换User-Agent为: {new_agent}")
                                # 切换代理
                                if hasattr(self, 'get_next_proxy'):
                                    self.get_next_proxy()
                                sleep(backoff_time)
                            else:
                                # 其他错误使用线性退避
                                sleep_time = random.uniform(5, 10)
                                logger.info(f"非432错误，等待 {sleep_time:.2f} 秒后重试")
                                sleep(sleep_time)
                    
                    # 如果该页面重试多次仍失败，可能是被限制了，采取更强的反爬措施
                    if not page_success:
                        logger.error(f"第 {page} 页微博在 {max_page_retries} 次尝试后仍然失败，执行紧急恢复策略")
                        # 切换代理
                        if hasattr(self, 'get_next_proxy'):
                            self.get_next_proxy()
                        # 切换User-Agent
                        if hasattr(self, 'user_agents') and self.user_agents:
                            new_agent = random.choice(self.user_agents)
                            self.headers['User-Agent'] = new_agent
                            logger.info(f"已切换User-Agent为: {new_agent}")
                        # 强制延迟较长时间
                        recovery_delay = random.uniform(30, 60)
                        logger.info(f"执行强制恢复策略，延长等待时间 {recovery_delay:.2f} 秒")
                        sleep(recovery_delay)
                    
                    # 通过加入随机等待避免被限制
                    if (page - page1) % random_pages == 0 and page < page_count and page_success:
                        # 增加随机延迟时间范围，使行为更不可预测
                        sleep_time = random.uniform(8, 15)
                        logger.info(f"页面爬取批次完成，随机延迟 {sleep_time:.2f} 秒")
                        sleep(sleep_time)
                        page1 = page
                        # 随机调整下次等待的页面数
                        random_pages = random.randint(2, 6)

                # 最后写入数据
                if wrote_count < self.got_count:
                    self.write_data(wrote_count)
            
            logger.info("微博爬取完成，共爬取%d条微博", self.got_count)
            
        except Exception as e:
            logger.error(f"get_pages函数执行出错: {str(e)}")
            logger.exception(e)
            # 在异常发生后也添加随机延迟，避免立即重试导致的反爬
            sleep(random.uniform(10, 20))

    def get_user_config_list(self, file_path):
        """获取文件中的微博id信息"""
        with open(file_path, "rb") as f:
            try:
                lines = f.read().splitlines() 
                lines = [line.decode("utf-8-sig") for line in lines]
            except UnicodeDecodeError:
                logger.error("%s文件应为utf-8编码，请先将文件编码转为utf-8再运行程序", file_path)
                sys.exit()
            user_config_list = []
            # 分行解析配置，添加到user_config_list
            for line in lines:
                info = line.strip().split(" ")    # 去除字符串首尾空白字符
                if len(info) > 0 and info[0].isdigit():
                    user_config = {}
                    user_config["user_id"] = info[0]
                    # 根据配置文件行的字段数确定 since_date 的值
                    if len(info) == 3:
                        if self.is_datetime(info[2]):
                            user_config["since_date"] = info[2]
                        elif self.is_date(info[2]):
                            user_config["since_date"] = "{}T00:00:00".format(info[2])
                        elif info[2].isdigit():
                            since_date = date.today() - timedelta(int(info[2]))
                            user_config["since_date"] = since_date.strftime(DTFORMAT)
                        else:
                            logger.error("since_date 格式不正确，请确认配置是否正确")
                            sys.exit()
                    else:
                        user_config["since_date"] = self.since_date
                    # 若超过3个字段，则第四个字段为 query_list                    
                    if len(info) > 3:
                        user_config["query_list"] = info[3].split(",")
                    else:
                        user_config["query_list"] = self.query_list
                    if user_config not in user_config_list:
                        user_config_list.append(user_config)
        return user_config_list

    def initialize_info(self, user_config):
        """初始化爬虫信息"""
        self.weibo = []
        self.user = {}
        self.user_config = user_config
        self.got_count = 0
        self.weibo_id_list = []

    def start(self):
        """运行爬虫"""
        try:
            # 初始随机延迟，模拟真实用户行为
            initial_delay = random.uniform(3, 8)
            logger.info(f"爬虫启动前随机延迟 {initial_delay:.2f} 秒")
            sleep(initial_delay)
            
            # 记录连续失败次数，用于触发紧急措施
            consecutive_failures = 0
            
            for user_config_idx, user_config in enumerate(self.user_config_list):
                try:
                    logger.info(f"处理用户配置 {user_config_idx + 1}/{len(self.user_config_list)}")
                    
                    if len(user_config["query_list"]):
                        for query_idx, query in enumerate(user_config["query_list"]):
                            self.query = query
                            self.initialize_info(user_config)
                            logger.info(f"开始抓取查询: {query}")
                            self.get_pages()
                            
                            # 查询之间添加随机延迟
                            if query_idx < len(user_config["query_list"]) - 1:
                                query_delay = random.uniform(5, 12)
                                logger.info(f"查询间随机延迟 {query_delay:.2f} 秒")
                                sleep(query_delay)
                    else:
                        self.initialize_info(user_config)
                        self.get_pages()
                    
                    logger.info("信息抓取完毕")
                    logger.info("*" * 100)
                    
                    if self.user_config_file_path and self.user:
                        self.update_user_config_file(self.user_config_file_path)
                    
                    # 用户配置之间添加随机延迟，避免密集请求
                    if user_config_idx < len(self.user_config_list) - 1:
                        user_delay = random.uniform(10, 20)
                        logger.info(f"用户配置间随机延迟 {user_delay:.2f} 秒")
                        sleep(user_delay)
                    
                    # 重置失败计数
                    consecutive_failures = 0
                    
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"处理用户配置时出错: {str(e)}")
                    logger.exception(e)
                    
                    # 失败处理策略
                    if consecutive_failures >= 3:
                        # 连续失败触发紧急措施
                        logger.warning(f"连续失败 {consecutive_failures} 次，触发紧急措施")
                        
                        # 切换代理和User-Agent
                        if hasattr(self, 'get_next_proxy'):
                            self.get_next_proxy()
                        
                        # 延长恢复等待时间
                        emergency_delay = random.uniform(30, 60)
                        logger.info(f"紧急恢复延迟 {emergency_delay:.2f} 秒")
                        sleep(emergency_delay)
                    else:
                        # 普通失败，线性退避
                        recovery_delay = random.uniform(15, 30)
                        logger.info(f"恢复延迟 {recovery_delay:.2f} 秒")
                        sleep(recovery_delay)
                        
        except Exception as e:
            logger.error("爬虫主程序发生异常")
            logger.exception(e)
            
            # 最后尝试恢复
            final_delay = random.uniform(60, 120)
            logger.info(f"最终恢复延迟 {final_delay:.2f} 秒")
            sleep(final_delay)


def handle_config_renaming(config, oldName, newName):
    if oldName in config and newName not in config:
        config[newName] = config[oldName]
        del config[oldName]

def get_config():
    """获取config.json文件信息"""
    config_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + "config.json"
    if not os.path.isfile(config_path):
        logger.warning(
            "当前路径：%s 不存在配置文件config.json",
            (os.path.split(os.path.realpath(__file__))[0] + os.sep),
        )
        sys.exit()
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.loads(f.read())
            # 重命名一些key, 但向前兼容
            handle_config_renaming(config, oldName="filter", newName="only_crawl_original")
            handle_config_renaming(config, oldName="result_dir_name", newName="user_id_as_folder_name")
            return config
    except ValueError:
        logger.error(
            "config.json 格式不正确，请参考 " "https://github.com/dataabc/weibo-crawler#3程序设置"
        )
        sys.exit()


def main():
    try:
        config = get_config()
        wb = Weibo(config)
        wb.start()  # 爬取微博信息
        if const.NOTIFY["NOTIFY"]:
            push_deer("更新了一次微博")
    except Exception as e:
        if const.NOTIFY["NOTIFY"]:
            push_deer("weibo-crawler运行出错，错误为{}".format(e))
        logger.exception(e)


if __name__ == "__main__":
    main()
