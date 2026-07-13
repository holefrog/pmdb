#!/bin/bash
# ============================================================
# PMDB 运行脚本
# 用法：./run.sh
# 安装目录由 Ansible 的 pmdb_install_dir 决定，
# 默认与本脚本位于同一目录。
# ============================================================

set -e

# 脚本自身所在目录即安装目录（支持从任意路径调用）
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${INSTALL_DIR}/venv"
CONFIG_FILE="${INSTALL_DIR}/config.ini"

echo "============================================"
echo "PMDB - 个人电影数据库工具"
echo "安装目录: ${INSTALL_DIR}"
echo "============================================"

# 检查 config.ini 是否存在（需先运行 Ansible 部署）
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "❌ 错误：config.ini 不存在"
    echo "   请先运行 Ansible 部署："
    echo "   ansible-playbook ansible/playbook.yml -e @secrets.yml"
    echo "   （自定义目录）-e \"pmdb_install_dir=${INSTALL_DIR}\""
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -f "${VENV_DIR}/bin/python" ]; then
    echo "❌ 错误：虚拟环境不存在 (${VENV_DIR})"
    echo "   请先运行 Ansible 部署："
    echo "   ansible-playbook ansible/playbook.yml -e @secrets.yml"
    exit 1
fi

echo "✅ 虚拟环境: ${VENV_DIR}"
echo "✅ 配置文件: ${CONFIG_FILE}"
echo ""

# 激活虚拟环境并运行
source "${VENV_DIR}/bin/activate"
echo "🚀 启动 PMDB..."
echo ""
cd "${INSTALL_DIR}"
python main.py

echo ""
echo "============================================"
echo "✅ PMDB 运行完成！"
echo "输出文件: ${INSTALL_DIR}/output.html"
echo "============================================"
