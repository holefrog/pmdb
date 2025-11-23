#!/bin/bash

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python3 first."
    exit 1
fi

# 设置虚拟环境路径为用户主目录下的 'venv' 文件夹
VENV_DIR="$HOME/venv"

# 创建虚拟环境
echo "Creating virtual environment in: $VENV_DIR"
# 可选：如果已存在，先删除旧环境
if [ -d "$VENV_DIR" ]; then
    echo "Existing virtual environment found. Removing old one first..."
    rm -rf "$VENV_DIR"
fi
python3 -m venv "$VENV_DIR"

# 激活虚拟环境 (注意：这里只是为了在脚本内部安装依赖，对用户环境无影响)
echo "Activating virtual environment for dependency installation..."
source "$VENV_DIR/bin/activate"

# 升级 pip
echo "Upgrading pip..."
pip install --upgrade pip

# 安装所有必要依赖（新增 jinja2）
echo "Installing all required libraries: ..."
pip install selenium webdriver-manager requests beautifulsoup4 jinja2

# 安装完成提示
echo "Setup complete! The virtual environment is located at: $VENV_DIR"
echo "To activate it manually, run:"
echo "source $VENV_DIR/bin/activate"
