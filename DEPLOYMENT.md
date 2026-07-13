# PMDB Ansible 部署指南

## 前置要求

```bash
# 安装 Ansible
pip install ansible

# 或使用包管理器（推荐）
# macOS
brew install ansible

# Ubuntu/Debian
sudo apt-get install ansible

# 验证 Ansible 安装
ansible --version
```

---

## 部署步骤

### 1️⃣ 准备密钥配置

```bash
# 复制示例配置
cp secrets.yml.example secrets.yml

# 编辑并填入真实的 API 密钥
vi secrets.yml
```

`secrets.yml` 文件示例：
```yaml
---
mistral_api_key: "6YAkqJijWy5ogFNiwWejeMReX9s7awc4"
omdb_api_key: "bc48eae4"
```

⚠️ **注意**：`secrets.yml` 已加入 `.gitignore`，不会被提交到版本控制。

---

### 2️⃣ 运行 Ansible 部署

```bash
# 执行部署（本地部署）
ansible-playbook deploy.yml -i localhost, -c local

# 或使用 sudo（如果需要）
ansible-playbook deploy.yml -i localhost, -c local -K
```

**部署过程会**：
- ✅ 检查 Python 版本
- ✅ 验证 `secrets.yml` 存在
- ✅ 创建 Python 虚拟环境（`venv/`）
- ✅ 升级 pip
- ✅ 安装所有项目依赖
- ✅ 从 `secrets.yml` + `config.ini.j2` 生成 `config.ini`
- ✅ 验证配置文件有效性

---

### 3️⃣ 运行应用

#### 方式一：使用 `run.sh` 脚本（推荐）

```bash
./run.sh
```

#### 方式二：手动激活 venv

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行应用
python main.py
```

---

## 目录结构

```
pmdb/
├── deploy.yml                 # Ansible playbook
├── secrets.yml                # ⚠️ 实际密钥（.gitignore）
├── secrets.yml.example        # ✅ 示例（提交到版本控制）
├── config.ini                 # ⚠️ 生成的配置（.gitignore）
├── config.ini.j2              # ✅ Jinja2 模板
├── run.sh                      # 应用运行脚本
├── venv/                       # ⚠️ Python 虚拟环境（.gitignore）
├── main.py
├── scraper.py
├── movie_api_service.py
├── mistral_service.py
├── config_reader.py
├── html_generator.py
├── requirements.txt
└── ...
```

---

## 常见问题

### Q1: 部署失败，提示 `secrets.yml not found`

**A**: 执行以下命令：
```bash
cp secrets.yml.example secrets.yml
# 然后编辑 secrets.yml，填入真实的 API 密钥
vi secrets.yml
```

---

### Q2: 如何更新 API 密钥？

**A**: 修改 `secrets.yml`，然后重新运行部署：
```bash
vi secrets.yml
ansible-playbook deploy.yml -i localhost, -c local
```

新的 `config.ini` 会被自动生成（旧版本会自动备份为 `config.ini.1`）。

---

### Q3: 虚拟环境已存在，需要重新创建吗？

**A**: 不需要。Playbook 会检测 `venv/` 是否已存在，只在不存在时创建。如需强制重新创建：

```bash
rm -rf venv/
ansible-playbook deploy.yml -i localhost, -c local
```

---

### Q4: 如何验证部署是否成功？

**A**: 检查以下项目：

```bash
# 1. 虚拟环境存在
test -d venv && echo "✅ venv exists"

# 2. config.ini 已生成
test -f config.ini && echo "✅ config.ini exists"

# 3. 配置文件有效
python -m configparser config.ini && echo "✅ config.ini is valid"

# 4. 依赖已安装
venv/bin/pip list | grep -E "requests|beautifulsoup|playwright"
```

---

### Q5: 如何清理部署？

**A**:
```bash
# 保留配置和依赖（推荐）
# 只删除日志和输出
rm -f pmdb.log output.html

# 完全清理（重新开始）
rm -rf venv/ config.ini pmdb.log output.html
ansible-playbook deploy.yml -i localhost, -c local
```

---

## 安全最佳实践

1. **绝不提交 `secrets.yml`** — 仓库中只提交 `secrets.yml.example`
2. **设置合适的文件权限** — `config.ini` 生成时权限为 `0600`（只有所有者可读写）
3. **定期轮换 API 密钥** — 修改 `secrets.yml` 后重新部署
4. **备份敏感文件** — 部署时旧 `config.ini` 自动保存为 `config.ini.1`

---

## 故障排查

### 问题：Ansible 找不到 Python

```bash
# 检查 Python 版本
python3 --version

# 如果提示找不到，安装 Python 3
sudo apt-get install python3 python3-venv
```

### 问题：权限不足

```bash
# 使用 -K 参数要求输入 sudo 密码
ansible-playbook deploy.yml -i localhost, -c local -K
```

### 问题：依赖安装失败

```bash
# 检查网络连接
ping pypi.org

# 清除 pip 缓存
venv/bin/pip cache purge

# 重新安装
venv/bin/pip install -r requirements.txt --no-cache-dir
```

---

## 后续维护

### 定期更新依赖

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

### 监控日志

```bash
tail -f pmdb.log
```

### 定期备份输出

```bash
cp output.html output.html.backup_$(date +%Y%m%d_%H%M%S)
```

---

## 相关文件说明

| 文件 | 说明 | 提交版本控制? |
|------|------|--------------|
| `deploy.yml` | Ansible playbook | ✅ 是 |
| `secrets.yml` | 实际 API 密钥 | ❌ 否 |
| `secrets.yml.example` | 示例密钥模板 | ✅ 是 |
| `config.ini` | 生成的配置文件 | ❌ 否 |
| `config.ini.j2` | Jinja2 配置模板 | ✅ 是 |
| `run.sh` | 应用运行脚本 | ✅ 是 |
| `venv/` | Python 虚拟环境 | ❌ 否 |

---

更新日期：2026-07-12
