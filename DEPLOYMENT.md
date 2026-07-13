# PMDB Ansible 部署指南

## 前置要求

```bash
# Ubuntu/Debian
sudo apt-get install ansible

# pip 安装
pip install ansible

# 验证
ansible --version
```

---

## 部署步骤

### 1️⃣ 准备密钥配置

```bash
cp secrets.yml.example secrets.yml
vim secrets.yml
```

填写以下必填项：
- `translate_provider`：翻译提供商（`mistral` / `openai` / `groq` / `nvidia` / `gemini`）
- 对应提供商的 API 密钥（如 `mistral_api_key`）
- `omdb_api_key`：OMDb API 密钥

⚠️ `secrets.yml` 已加入 `.gitignore`，不会提交到版本控制。

### 2️⃣ 运行 Ansible 部署

```bash
ansible-playbook ansible/playbook.yml -e @secrets.yml
```

**部署过程会：**
- ✅ 检查 Python 版本
- ✅ 验证 `secrets.yml` 字段
- ✅ 创建 Python 虚拟环境（`venv/`）
- ✅ 安装所有项目依赖
- ✅ 安装 Playwright Chromium（失败则静默跳过，程序运行时尝试系统浏览器）
- ✅ 从 `secrets.yml` + `config.ini.j2` 生成 `config.ini`（权限 0600）
- ✅ 验证配置文件有效性

### 3️⃣ 运行应用

```bash
./run.sh
```

---

## 目录结构

```
pmdb/
├── ansible/
│   ├── playbook.yml                # 主 Playbook
│   ├── inventory/hosts.ini         # 本地清单
│   └── roles/pmdb/
│       ├── tasks/main.yml          # 部署任务
│       ├── templates/config.ini.j2 # Jinja2 配置模板
│       └── vars/main.yml           # 角色变量
├── secrets.yml                     # ⚠️ 实际密钥（.gitignore）
├── secrets.yml.example             # ✅ 示例（提交到版本控制）
├── config.ini                      # ⚠️ Ansible 生成（.gitignore）
├── run.sh                          # 运行脚本
└── [Python 源文件]
```

---

## 文件对照表

| 文件 | 说明 | 提交版本控制? |
|------|------|:---:|
| `ansible/playbook.yml` | 主 Playbook | ✅ |
| `ansible/roles/pmdb/templates/config.ini.j2` | 配置模板 | ✅ |
| `secrets.yml` | 实际 API 密钥 | ❌ |
| `secrets.yml.example` | 示例模板 | ✅ |
| `config.ini` | 生成的配置 | ❌ |
| `run.sh` | 运行脚本 | ✅ |
| `venv/` | Python 虚拟环境 | ❌ |

---

## 常见问题

**Q: 如何切换翻译提供商？**
```bash
vim secrets.yml   # 修改 translate_provider 和对应 API 密钥
ansible-playbook ansible/playbook.yml -e @secrets.yml  # 重新部署
```

**Q: 如何更新 API 密钥？**
```bash
vim secrets.yml
ansible-playbook ansible/playbook.yml -e @secrets.yml
```
新的 `config.ini` 会自动生成，旧版本备份为 `config.ini.1`。

**Q: 如何验证部署成功？**
```bash
test -d venv && echo "✅ venv OK"
test -f config.ini && echo "✅ config.ini OK"
grep "translate_provider" config.ini
```

**Q: 如何清理重新部署？**
```bash
rm -rf venv/ config.ini
ansible-playbook ansible/playbook.yml -e @secrets.yml
```

---

## 安全最佳实践

1. **绝不提交 `secrets.yml`** — 仅提交 `secrets.yml.example`
2. **`config.ini` 权限为 0600** — 只有所有者可读写
3. **定期轮换 API 密钥** — 修改 `secrets.yml` 后重新部署

---

更新日期：2026-07-13
