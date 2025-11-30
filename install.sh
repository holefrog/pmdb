#!/bin/bash

# ============================================
# PMDB 安装脚本
# ============================================

set -e  # 遇到错误立即退出

echo "============================================"
echo "PMDB - 个人电影数据库工具 安装程序"
echo "============================================"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未安装 Python3，请先安装 Python 3.7+"
    exit 1
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ 检测到 Python 版本: $PYTHON_VERSION"

# 设置虚拟环境路径
VENV_DIR="$HOME/venv"

# 创建虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo "⚠️  检测到已存在的虚拟环境，删除旧环境..."
    rm -rf "$VENV_DIR"
fi

echo "📦 正在创建虚拟环境: $VENV_DIR"
python3 -m venv "$VENV_DIR"

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 升级 pip
echo "⬆️  升级 pip 到最新版本..."
pip install --upgrade pip -q

# 安装依赖（已移除 selenium 和 webdriver-manager）
echo "📥 安装依赖库..."
pip install -q requests beautifulsoup4 jinja2 urllib3 playwright

# 安装 Chromium 浏览器（仅 headless_shell）
echo "🌐 安装 Chromium 浏览器..."
python3 -m playwright install chromium  # 使用 Python 模块方式安装

# 创建配置文件（如果不存在）
if [ ! -f "config.ini" ]; then
    if [ -f "config.ini.example" ]; then
        echo "📝 复制配置文件模板..."
        cp config.ini.example config.ini
        echo "⚠️  请编辑 config.ini 并填入您的 DeepL API 密钥"
    else
        echo "⚠️  未找到 config.ini.example，请手动创建 config.ini"
    fi
else
    echo "✅ 配置文件已存在"
fi

echo ""
echo "============================================"
echo "✅ 安装完成！"
echo "============================================"
echo ""
echo "虚拟环境位置: $VENV_DIR"
echo ""
echo "下一步操作："
echo "1. 编辑 config.ini 并填入您的 DeepL API 密钥"
echo "2. 运行程序: ./pmdb.sh"
echo ""
echo "手动激活虚拟环境:"
echo "source $VENV_DIR/bin/activate"
echo "============================================"
