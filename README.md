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
| **多AI翻译** | 5 大提供商可配置，secrets.yml 中一键切换 |
| **安全配置** | API 密钥存 secrets.yml，Ansible 渲染生成 config.ini，不进版本控制 |

---

## 📦 依赖

- Python 3.8+
- `playwright`、`requests`、`beautifulsoup4`、`jinja2`

---

## 🚀 快速开始

### 前置要求

```bash
# 安装 Ansible
pip install ansible
# 或
sudo apt-get install ansible
```

### 1️⃣ 克隆项目

```bash
git clone https://github.com/your-repo/pmdb.git
cd pmdb
```

### 2️⃣ 配置密钥

```bash
cp secrets.yml.example secrets.yml
# 填入你的 API 密钥
vim secrets.yml
```

### 3️⃣ 运行 Ansible 部署

```bash
ansible-playbook ansible/playbook.yml -e @secrets.yml
```

部署会自动：创建 venv、安装依赖、安装 Chromium、生成 config.ini。

### 4️⃣ 运行程序

```bash
./run.sh
```

---

## ⚙️ 配置说明

所有配置均在 `secrets.yml` 中管理，部署后生成 `config.ini`：

```yaml
# 翻译提供商（mistral / openai / groq / nvidia / gemini）
translate_provider: "mistral"

# 各提供商 API 密钥（填写你使用的）
mistral_api_key: "YOUR_KEY"
openai_api_key: ""
groq_api_key: ""
nvidia_api_key: ""
gemini_api_key: ""

# OMDb API 密钥（免费注册：https://www.omdbapi.com/apikey.aspx）
omdb_api_key: "YOUR_KEY"

# 运行参数
max_workers: 10
max_movies: 100
```

---

## 📂 项目结构

```
pmdb/
├── ansible/
│   ├── playbook.yml                # 主 Playbook
│   ├── inventory/hosts.ini         # 本地清单
│   └── roles/pmdb/
│       ├── tasks/main.yml          # 部署任务
│       ├── templates/config.ini.j2 # 配置模板
│       └── vars/main.yml           # 角色变量
├── secrets.yml                     # ⚠️ 真实密钥（.gitignore）
├── secrets.yml.example             # ✅ 示例（提交）
├── config.ini                      # ⚠️ Ansible 生成（.gitignore）
├── run.sh                          # 运行脚本
├── main.py                         # 主程序入口
├── scraper.py                      # 抓取模块（多源 Fallback）
├── movie_api_service.py            # OMDb 查询（多变体搜索）
├── translate_service.py            # 多AI翻译服务
├── config_reader.py                # 配置文件解析
├── html_generator.py               # HTML 生成
└── requirements.txt
```

---

## ❓ 常见问题

**Q: Playwright Chromium 安装失败？**
`scraper.py` 会自动寻找系统中的 `google-chrome` 或 `chromium-browser`。

**Q: 某些电影找不到信息？**
程序有四阶段搜索（精确 → 年份±1 → 模糊 → AI 兜底），找不到的会自动跳过。

**Q: 如何切换翻译提供商？**
修改 `secrets.yml` 中的 `translate_provider`，重新运行 Ansible 即可。

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
