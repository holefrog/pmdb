![Logo](logo.png)

---

# 📽️ PMDB - 个人电影数据库工具 (Personal Movie Database Tool)

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📖 简介 (Introduction)

`pmdb` 是一个 **自动化电影信息收集与展示工具**，它的工作流程如下：

- 🎯 **智能抓取**：使用 `Playwright` 从 The Pirate Bay 获取最新的 Top 100 热门电影列表。
- 🔍 **精准查询**：调用 `OMDb API` 自动获取电影详细信息（包括评分、英文简介、海报图），替代了不稳定的直接网页解析。
- 🌐 **批量翻译**：接入 `Mistral API` 大语言模型，将英文简介批量且准确地翻译为中文。
- 📄 **美观呈现**：基于 `Jinja2` 模板引擎，生成包含海报、双语简介和评分的精美 HTML 电影展示页面。
- ⚡ **高效并发**：采用多线程并行处理，显著缩短数据获取时间。

---

## ✨ 主要特性

| 特性 | 说明 |
|------|------|
| **稳定爬取** | 使用 Playwright 无头浏览器模拟真实访问，轻松应对简单反爬。 |
| **可靠数据源** | 全面切换至 OMDb API 替代 IMDb 网页直爬，数据结构化且不易失效。 |
| **智能翻译** | 借助 Mistral 大模型进行批量翻译，不仅准确度高，还大幅减少 API 调用次数。 |
| **并行处理** | 支持自定义多线程并发数，大幅提升电影详情的获取速度。 |
| **模块化设计** | 职责分离清晰（爬虫、API 服务、翻译、渲染），方便二次开发和维护。 |

---

## 📦 依赖 (Dependencies)

本项目需要 **Python 3.7+**，主要依赖库包括：

- `playwright` (用于网页自动化抓取)
- `requests` (用于 API 请求)
- `beautifulsoup4` (用于 HTML 解析)
- `jinja2` (用于 HTML 模板渲染)

> 💡 **注意**：项目采用 Playwright 替代了早期的 Selenium，更加轻量稳定！

---

## 🚀 快速开始 (Quick Start)

### 1️⃣ 克隆项目

```bash
git clone https://github.com/your-repo/pmdb.git
cd pmdb
```

### 2️⃣ 运行安装脚本

```bash
chmod +x *.sh
./install.sh
```

**安装脚本会自动：**
- 在项目本地创建 `venv` 虚拟环境。
- 安装所有必要的 Python 依赖包。
- 安装 Playwright 所需的 Chromium 浏览器内核（若官方版安装失败，程序运行时会自动寻找系统自带的 Chrome/Chromium）。

### 3️⃣ 获取并配置 API 密钥

本项目需要两个 API 密钥才能正常工作：
1. **OMDb API 密钥**：获取电影详情。[免费注册 OMDb Key](https://www.omdbapi.com/apikey.aspx)（每日 1000 次免费额度）。
2. **Mistral API 密钥**：用于文本翻译。[注册 Mistral AI](https://console.mistral.ai/)。

复制配置模板并进行编辑：

```bash
cp config.ini.example config.ini
```

在 `config.ini` 中填入你的密钥：

```ini
[Mistral]
api_key_mistral="<YOUR_MISTRAL_API_KEY>"

[OMDb_API]
OMDB_KEY="<YOUR_OMDB_API_KEY>"
```

### 4️⃣ 运行程序

```bash
./pmdb.sh
```

脚本将自动激活虚拟环境并执行主程序 `main.py`。运行完成后，将在浏览器中自动打开生成的 `output.html`。

---

## ⚙️ 配置说明 (Configuration)

你可以通过修改 `config.ini` 来自定义程序的运行行为，无需修改代码：

```ini
[Settings]
# 并行工作线程数（建议 3-10，提升数据抓取速度）
max_workers=5

# 最大处理电影数量
max_movies=100

# Mistral 每批翻译文本数量（建议 10-50）
mistral_batch_size=10

# 网络请求超时时间（秒）
request_timeout=10
```

---

## 📂 项目结构 (Project Structure)

```
pmdb/
├── main.py              # 主程序入口，统筹各模块
├── scraper.py           # 抓取模块 (Playwright + The Pirate Bay)
├── movie_api_service.py # 电影详情获取模块 (OMDb API)
├── mistral_service.py   # 翻译服务模块 (Mistral API)
├── html_generator.py    # HTML 生成模块 (Jinja2)
├── config_reader.py     # 配置文件解析模块
├── template.html        # HTML 渲染模板
├── config.ini.example   # 配置文件模板
├── pmdb.sh              # 运行脚本
├── install.sh           # 安装脚本
├── README.md            # 项目说明
└── .gitignore           # Git 忽略配置
```

---

## ❓ 常见问题 (FAQ)

### Q1: 提示 Playwright Chromium 安装失败怎么办？
**A**: `install.sh` 如果在下载 Chromium 时遇到网络或系统兼容性问题，脚本会继续执行。`scraper.py` 已经做了兼容，会自动尝试寻找您 Linux 系统中安装的 `google-chrome` 或 `chromium-browser`。您也可以手动安装 Chrome。

### Q2: 为什么有些电影在 HTML 中没有显示，或者控制台提示"未找到"？
**A**: 
1. 电影名称不规范或缺少年份。
2. OMDb 数据库中确实未收录该影片。
程序设计了容错机制，会自动跳过这些无法获取信息的电影并继续处理后续列表。

### Q3: 翻译结果数量不匹配或翻译报错？
**A**: 请检查网络连接以及 Mistral API 的配额。如果文本过长，你可以尝试在 `config.ini` 中减小 `mistral_batch_size`。

---

## 🤝 贡献 (Contributing)

欢迎提交 Issue 和 Pull Request！

**待办事项 (TODO)**：
- [ ] 支持本地缓存避免对同一部电影重复调用 OMDb API
- [ ] 增加豆瓣 API 或 TMDB 等备用数据源
- [ ] 支持将数据导出为 CSV / JSON 格式

---

## 📄 许可证 (License)

[MIT License](LICENSE)
