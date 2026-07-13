# PMDB 快速开始

## ⚡ 30 秒快速部署

### 1. 初始化密钥配置

```bash
cp secrets.yml.example secrets.yml
# 使用文本编辑器打开并填入真实的 API 密钥
vim secrets.yml
```

### 2. 一键部署

```bash
./quick_deploy.sh
```

脚本会自动：
- ✅ 检查 Ansible 是否安装
- ✅ 验证 `secrets.yml` 配置
- ✅ 创建虚拟环境
- ✅ 安装所有依赖
- ✅ 生成 `config.ini`

### 3. 运行应用

```bash
./run.sh
```

---

## 手动部署（如果快速部署失败）

```bash
# 1. 复制示例配置
cp secrets.yml.example secrets.yml

# 2. 编辑配置（填入 API 密钥）
vi secrets.yml

# 3. 运行 Ansible playbook
ansible-playbook deploy.yml -i localhost, -c local

# 4. 运行应用
./run.sh
```

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `quick_deploy.sh` | 快速部署脚本（推荐） |
| `deploy.yml` | Ansible playbook |
| `secrets.yml` | ⚠️ API 密钥（不提交） |
| `secrets.yml.example` | 配置示例 |
| `config.ini.j2` | 配置模板 |
| `run.sh` | 应用运行脚本 |
| `venv/` | Python 虚拟环境 |

---

## 常见问题

**Q: Ansible 未安装**
```bash
pip install ansible
# 或
brew install ansible
```

**Q: 权限被拒绝**
```bash
chmod +x quick_deploy.sh run.sh
./quick_deploy.sh -K  # -K 需要输入密码
```

**Q: API 密钥错误**
```bash
vi secrets.yml
./quick_deploy.sh  # 重新部署会更新 config.ini
```

---

详见 [DEPLOYMENT.md](DEPLOYMENT.md) 获取完整文档。
