#!/bin/bash
# ============================================================
# PMDB 简单部署脚本
# 用法：./deploy.sh [额外 ansible-playbook 参数]
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYBOOK="${SCRIPT_DIR}/ansible/playbook.yml"

echo "🚀 开始执行 Ansible playbook..."
ansible-playbook "$PLAYBOOK" -e "@${SCRIPT_DIR}/ansible/secrets.yml" "$@"

