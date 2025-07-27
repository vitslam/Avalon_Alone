#!/usr/bin/env python3
"""
阿瓦隆 Alone 服务器启动脚本
"""

import uvicorn
import os
import sys
from pathlib import Path

def main():
    """启动服务器"""
    # 检查是否在正确的目录
    if not Path("backend").exists():
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 设置环境变量
    os.environ.setdefault("PYTHONPATH", ".")
    
    # 启动服务器
    print("启动阿瓦隆 Alone 服务器...")
    print("访问地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("前端界面: 打开 frontend/index.html")
    print("按 Ctrl+C 停止服务器")
    
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 