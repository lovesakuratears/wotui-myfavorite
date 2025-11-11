#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博爬虫管理系统 - 服务启动脚本
用于启动Flask服务，提供API接口和静态文件访问
"""

import os
import sys
import argparse
from werkzeug.serving import run_simple
from werkzeug.middleware.proxy_fix import ProxyFix

# 确保当前目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入Flask应用实例
from service import app

# 配置代理修复，支持在反向代理环境中运行
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='微博爬虫管理系统服务启动脚本')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器监听地址（默认：0.0.0.0）')
    parser.add_argument('--port', type=int, default=5000, help='服务器监听端口（默认：5000）')
    parser.add_argument('--debug', action='store_true', default=False, help='启用调试模式')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    print(f"微博爬虫管理系统服务启动中...")
    print(f"监听地址: {args.host}:{args.port}")
    print(f"调试模式: {'是' if args.debug else '否'}")
    print(f"访问地址: http://{args.host}:{args.port}")
    print("按 Ctrl+C 停止服务")
    
    try:
        # 启动Flask服务
        run_simple(
            args.host,
            args.port,
            app,
            use_reloader=args.debug,
            use_debugger=args.debug,
            use_evalex=args.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"\n服务启动失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
