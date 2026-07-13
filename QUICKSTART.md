# PMDB 快速开始

## ⚡ 三步部署

### 1. 配置密钥

```bash
cp secrets.yml.example secrets.yml
vim secrets.yml   # 填入 API 密钥
```

### 2. Ansible 部署

```bash
ansible-playbook ansible/playbook.yml -e @secrets.yml
```

### 3. 运行

```bash
./run.sh
```

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `secrets.yml` | ⚠️ API 密钥（不提交） |
| `secrets.yml.example` | 配置示例（参考） |
| `ansible/playbook.yml` | Ansible 主 Playbook |
| `config.ini` | Ansible 生成的配置（不提交） |
| `run.sh` | 运行脚本 |

---

## 常见问题

**Ansible 未安装**
```bash
pip install ansible
```

**权限被拒绝**
```bash
chmod +x run.sh
```

**重新部署（更新密钥/依赖）**
```bash
vim secrets.yml
ansible-playbook ansible/playbook.yml -e @secrets.yml
```

---

详见 [DEPLOYMENT.md](DEPLOYMENT.md) 获取完整文档。
