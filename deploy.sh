#!/bin/bash
# ============================================================
# PMDB 简单部署脚本
# 用法：./deploy.sh [额外 ansible-playbook 参数]
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/ansible/secrets.yml"
PLAYBOOK="${SCRIPT_DIR}/ansible/playbook.yml"

# 如果 secrets 不存在则从 example 复制并提示
if [ ! -f "$SECRETS_FILE" ]; then
    echo "⚠️  $SECRETS_FILE 不存在，正在从模板复制..."
    cp "${SCRIPT_DIR}/ansible/secrets.yml.example" "$SECRETS_FILE"
    echo "❌ 请先编辑 $SECRETS_FILE 填入配置信息，然后重新运行本脚本。"
    exit 1
fi

echo "🚀 开始执行 Ansible playbook..."
ansible-playbook "$PLAYBOOK" -e "@$SECRETS_FILE" "$@"
