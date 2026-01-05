"""
WebUI启动脚本
用于快速启动策略触发点位展示服务
"""

import os
import sys
import subprocess

def main():
    # 添加父目录到Python路径
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    print("=" * 60)
    print("策略触发点位K线图WebUI")
    print("=" * 60)
    print()

    # 检查依赖
    print("检查依赖...")
    required_packages = ['flask', 'sqlalchemy', 'pandas', 'pymysql']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"缺少以下依赖: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return

    print("所有依赖已安装 ✓")
    print()

    # 启动Flask应用
    print("启动WebUI服务...")
    try:
        from app import app
        web_config = __import__('config').get_web_config()
        print(f"访问地址: http://{web_config['host']}:{web_config['port']}")
        print("按 Ctrl+C 停止服务")
        print("=" * 60)
        print()

        app.run(
            host=web_config['host'],
            port=web_config['port'],
            debug=True
        )
    except Exception as e:
        print(f"启动失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
