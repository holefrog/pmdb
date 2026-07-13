#!/bin/bash
# ============================================================
# PMDB 一键部署脚本
# 用法：./deploy.sh [选项]
#
# 选项：
#   --force-venv    强制重建 Python 虚拟环境
#   --check         空跑（Ansible dry-run，不实际修改）
#   -h, --help      显示帮助
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/secrets.yml"
PLAYBOOK="${SCRIPT_DIR}/ansible/playbook.yml"

# ── 颜色输出 ─────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; exit 1; }

# ── 参数解析 ─────────────────────────────────────────────────
FORCE_VENV=""
CHECK_MODE=""

for arg in "$@"; do
    case "$arg" in
        --force-venv) FORCE_VENV="-e force_venv_recreate=true" ;;
        --check)      CHECK_MODE="--check" ;;
        -h|--help)
            echo "用法: ./deploy.sh [--force-venv] [--check]"
            echo "  --force-venv  强制重建虚拟环境（升级依赖时使用）"
            echo "  --check       Ansible dry-run，不实际修改系统"
            exit 0
            ;;
        *) err "未知参数: $arg（使用 -h 查看帮助）" ;;
    esac
done

echo ""
echo "============================================"
echo " PMDB 部署脚本"
echo "============================================"
echo ""

# ── 前置检查 ─────────────────────────────────────────────────
echo "🔍 检查前置条件..."

# 检查 Ansible
if ! command -v ansible-playbook &>/dev/null; then
    err "Ansible 未安装。请先安装：\n  pip install ansible\n  或 sudo apt-get install ansible"
fi
ok "Ansible: $(ansible --version | head -1)"

# 检查 secrets.yml
if [ ! -f "${SECRETS_FILE}" ]; then
    warn "secrets.yml 不存在，正在从模板创建..."
    cp "${SCRIPT_DIR}/secrets.yml.example" "${SECRETS_FILE}"
    warn "请先编辑 secrets.yml 填入 API 密钥，然后重新运行 deploy.sh"
    echo ""
    echo "  vim ${SECRETS_FILE}"
    echo ""
    exit 1
fi
ok "secrets.yml: ${SECRETS_FILE}"

# 基本校验：确保不是未填写的占位符
if grep -q "<YOUR_" "${SECRETS_FILE}"; then
    warn "secrets.yml 中仍有未填写的占位符（<YOUR_...>）"
    warn "请编辑后重新运行: vim ${SECRETS_FILE}"
    exit 1
fi

# 检查 playbook
if [ ! -f "${PLAYBOOK}" ]; then
    err "Playbook 不存在: ${PLAYBOOK}"
fi
ok "Playbook: ${PLAYBOOK}"

echo ""

# ── 运行 Ansible ─────────────────────────────────────────────
if [ -n "${CHECK_MODE}" ]; then
    warn "DRY-RUN 模式（不会实际修改系统）"
fi
if [ -n "${FORCE_VENV}" ]; then
    warn "将强制重建虚拟环境"
fi

echo "🚀 开始部署..."
echo ""

ansible-playbook "${PLAYBOOK}" \
    -e "@${SECRETS_FILE}" \
    ${FORCE_VENV} \
    ${CHECK_MODE} \
    -v

echo ""
ok "部署完成！"
echo ""
echo "运行程序："
echo "  cd \$(grep 'deploy_dir' ${SCRIPT_DIR}/ansible/roles/pmdb/vars/main.yml | awk '{print \$2}')"
echo "  ./run.sh"
echo ""
