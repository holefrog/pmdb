![Logo](logo.png)

---

# 📽️ PMDB - 个人电影数据库工具

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📖 简介

`pmdb` 是一个**自动化电影信息收集与展示工具**，工作流程如下：

- 🎯 **多源抓取**：使用 `Playwright` 从 The Pirate Bay 等多个备用镜像获取 Top 100 热门电影，支持自动 Fallback。
- 🔍 **智能查询**：调用 `OMDb API` 获取电影详情（评分、简介、海报），多阶段搜索策略（精确 → 模糊 → AI 兜底）。
- 🌐 **多AI翻译**：支持 Mistral / OpenAI / Groq / Nvidia / Gemini 五大提供商，通过配置一键切换。
- 📄 **美观呈现**：基于 `Jinja2` 模板生成含海报、双语简介和评分的精美 HTML。
- ⚡ **高效并发**：多线程并行处理，显著缩短数据获取时间。

---

## ✨ 主要特性

| 特性 | 说明 |
|------|------|
| **多源 Fallback** | 内置 TPB 镜像列表，源站宕机自动降级，无需人工干预 |
| **智能去重** | 大小写无关 + `&`/`And` 标准化，避免同部电影重复 |
| **多阶段搜索** | 精确匹配 → 年份±1 → 模糊搜索 → AI 推理，命中率最大化 |
| **多AI翻译** | 5 大提供商可配置，`ansible/secrets.yml` 中一键切换 |
| **安全配置** | API 密钥存 `ansible/secrets.yml`，Ansible 渲染生成 `config.ini`，不进版本控制 |

---

## 📦 依赖

- Python 3.8+
- `playwright`、`requests`、`beautifulsoup4`、`jinja2`
- Ansible（部署时需要）

---

## 📂 项目结构

```
pmdb/
├── ansible/
│   ├── playbook.yml                # 主 Playbook
│   ├── inventory/hosts.ini         # 本地清单
│   └── roles/pmdb/
│       ├── tasks/main.yml          # 部署任务
│       ├── templates/config.ini.j2 # 配置模板（Jinja2）
│       └── vars/main.yml           # 角色变量
├── ansible/secrets.yml                     # ⚠️ 真实密钥（.gitignore，不提交）
├── ansible/secrets.yml.example             # ✅ 密钥示例（提交）
├── config.ini                      # ⚠️ Ansible 生成（.gitignore，不提交）
├── run.sh                          # 运行脚本
├── main.py                         # 主程序入口
├── scraper.py                      # 抓取模块（多源 Fallback）
├── movie_api_service.py            # OMDb 查询（多变体搜索）
├── translate_service.py            # 多AI翻译服务
├── config_reader.py                # 配置文件解析
├── html_generator.py               # HTML 生成
├── retry.py                        # 指数退避重试工具
└── requirements.txt
```

---

## 🚀 快速开始（3步）

### 前置要求

```bash
# Ubuntu/Debian
sudo apt-get install ansible

# 或 pip
pip install ansible
```

### 1️⃣ 配置密钥

```bash
cp ansible/secrets.yml.example ansible/secrets.yml
vim ansible/secrets.yml   # 填入 API 密钥
```

### 2️⃣ Ansible 部署

```bash
# 部署到当前目录（默认）
ansible-playbook ansible/playbook.yml -e @ansible/secrets.yml

# 指定安装目录（可选）
ansible-playbook ansible/playbook.yml -e @ansible/secrets.yml -e "deploy_dir=/opt/pmdb"
```

部署会自动：创建 venv、安装依赖、安装 Chromium、生成 `config.ini`（权限 0600）。

### 3️⃣ 运行程序

```bash
./run.sh
```

---

## ⚙️ 配置说明

所有配置均在 `ansible/secrets.yml` 中管理，Ansible 部署后渲染生成 `config.ini`。

### 必填项

```yaml
# 翻译提供商（mistral / openai / groq / nvidia / gemini）
translate_provider: "mistral"

# 对应提供商的 API 密钥
mistral_api_key: "YOUR_MISTRAL_KEY"

# OMDb API 密钥（免费注册：https://www.omdbapi.com/apikey.aspx）
omdb_api_key: "YOUR_OMDB_KEY"
```

### 可选项

```yaml
# 翻译模型（各提供商默认值）
mistral_translate_model: "mistral-large-latest"
openai_translate_model: "gpt-4o-mini"
groq_translate_model: "llama-3.3-70b-versatile"
nvidia_translate_model: "meta/llama-3.3-70b-instruct"
gemini_translate_model: "gemini-2.5-flash"

# IMDb AI 兜底查询（固定用 Mistral）
imdb_lookup_model: "mistral-small-latest"

# 运行参数
max_workers: 10        # 并发线程数
max_movies: 100        # 最大处理数量
request_timeout: 15    # 网络超时（秒）

# 自定义爬虫源（可选，内置 TPB 镜像已足够）
# scraper_urls:
#   - "https://thepiratebay.org/search.php?q=top100:207"
#   - "https://piratebay.live/search.php?q=top100:207"
#   - "https://tpb.party/search.php?q=top100:207"
```

---

## 🔧 部署详情

### Ansible 变量

| 变量 | 配置値 | 说明 |
|------|--------|------|
| `deploy_user` | `david` | 部署目标用户 |
| `deploy_dir` | `/home/david/Programs/Agent_Movie` | 程序安装目录（venv、config.ini 均在此目录下） |
| `pmdb_venv_dir` | `{{ deploy_dir }}/venv` | Python 虚拟环境路径 |
| `pmdb_config_output` | `{{ deploy_dir }}/config.ini` | 生成的配置文件路径 |

**修改部署目录：** 编辑 `ansible/roles/pmdb/vars/main.yml` 中的 `deploy_user` 和 `deploy_dir` 即可。

### 文件安全说明

| 文件 | 提交版本控制? | 说明 |
|------|:---:|------|
| `ansible/playbook.yml` | ✅ | 主 Playbook |
| `ansible/roles/pmdb/templates/config.ini.j2` | ✅ | 配置模板 |
| `ansible/secrets.yml` | ❌ | 真实 API 密钥 |
| `ansible/secrets.yml.example` | ✅ | 密钥示例模板 |
| `config.ini` | ❌ | Ansible 生成，权限 0600 |
| `venv/` | ❌ | Python 虚拟环境 |

---

## 🔄 日常操作

### 更新 API 密钥 / 切换翻译提供商

```bash
vim ansible/secrets.yml
ansible-playbook ansible/playbook.yml -e @ansible/secrets.yml
```

### 监控日志

```bash
tail -f pmdb.log
```

### 验证部署

```bash
test -d venv && echo "✅ venv OK"
test -f config.ini && echo "✅ config.ini OK"
grep "translate_provider" config.ini
```

### 完全重新部署

```bash
rm -rf venv/ config.ini
ansible-playbook ansible/playbook.yml -e @ansible/secrets.yml
```

---

## ❓ 常见问题

**Q: Ansible 未安装？**
```bash
pip install ansible
```

**Q: Playwright Chromium 安装失败？**
`scraper.py` 会自动寻找系统中的 `google-chrome` 或 `chromium-browser`，无需手动处理。

**Q: 某些电影找不到信息？**
程序有四阶段搜索（精确 → 年份±1 → 模糊 → AI 兜底），找不到的自动跳过，不影响其他电影。

**Q: 如何切换翻译提供商？**
修改 `ansible/secrets.yml` 中的 `translate_provider` 和对应密钥，重新运行 Ansible 即可。

**Q: `config.ini` 误删怎么办？**
重新运行 `ansible-playbook ansible/playbook.yml -e @ansible/secrets.yml` 即可重新生成。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

**TODO**：
- [ ] 本地缓存，避免重复调用 OMDb API
- [ ] 增加豆瓣/TMDB 等备用数据源
- [ ] 支持 CSV/JSON 导出

---

## 📄 许可证

[MIT License](LICENSE)
