#!/bin/bash
# ============================================================
# PMDB 运行脚本
# 用法：./run.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CONFIG_FILE="$SCRIPT_DIR/config.ini"

echo "============================================"
echo "PMDB - 个人电影数据库工具"
echo "============================================"

# 检查 config.ini 是否存在（需先运行 Ansible 部署）
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 错误：config.ini 不存在"
    echo "   请先运行 Ansible 部署："
    echo "   ansible-playbook ansible/playbook.yml -e @secrets.yml"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "❌ 错误：虚拟环境不存在（$VENV_DIR）"
    echo "   请先运行 Ansible 部署："
    echo "   ansible-playbook ansible/playbook.yml -e @secrets.yml"
    exit 1
fi

echo "✅ 检测到虚拟环境: $VENV_DIR"
echo "✅ 检测到配置文件: $CONFIG_FILE"
echo ""

# 激活虚拟环境并运行
source "$VENV_DIR/bin/activate"
echo "🚀 启动 PMDB..."
echo ""
cd "$SCRIPT_DIR"
python main.py

echo ""
echo "============================================"
echo "✅ PMDB 运行完成！"
echo "输出文件: $SCRIPT_DIR/output.html"
echo "============================================"
