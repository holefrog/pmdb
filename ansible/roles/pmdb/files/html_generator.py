"""
HTML 输出生成器。

模板结构（output/ 子目录）：
  output/template.html  — Jinja2 HTML 骨架，含 {{ styles }} 占位符
  output/template.css   — 独立 CSS 文件，渲染时内联注入

输出文件 output.html 为自包含单文件（内联 CSS），无需依赖外部资源。
"""
import os
import logging
import webbrowser
from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)

# ── 默认模板目录（相对于本文件所在目录）────────────────────
_DEFAULT_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "output")
_DEFAULT_HTML_NAME    = "template.html"
_DEFAULT_CSS_NAME     = "template.css"
_DEFAULT_OUTPUT_PATH  = "output.html"

# ── 内置后备模板（output/ 目录缺失时使用）───────────────────
_FALLBACK_CSS = """
* { box-sizing: border-box; }
body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
h1 { text-align: center; color: #333; }
.container { display: flex; flex-wrap: wrap; justify-content: space-between; max-width: 1400px; margin: 0 auto; }
.movie-item { width: 49%; margin-bottom: 20px; border: 1px solid #ddd; padding: 15px; background: white; border-radius: 5px; position: relative; }
img { max-width: 150px; height: auto; margin-right: 15px; float: left; cursor: pointer; border-radius: 3px; }
img:hover { opacity: 0.8; }
.movie-title { font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }
.rating-display { display: flex; align-items: center; margin-bottom: 10px; }
.linear-gauge-container { width: 100px; height: 10px; background-color: #e0e0e0; border-radius: 5px; margin-left: 10px; overflow: hidden; }
.linear-gauge-bar { height: 100%; border-radius: 5px; }
.rating-score { font-weight: bold; }
.rating-low, .fill-low { color: #a9a9a9; background-color: #a9a9a9; }
.rating-mid, .fill-mid { color: #4a90e2; background-color: #4a90e2; }
.rating-high, .fill-high { color: #ff6b6b; background-color: #ff6b6b; }
.summary-cn { color: #4a90e2; margin-top: 10px; line-height: 1.6; }
.summary-en { color: #666; margin-top: 8px; font-style: italic; line-height: 1.5; }
.movie-content { overflow: hidden; }
.counter { position: absolute; bottom: 15px; right: 15px; font-size: 1.5em; font-weight: bold; color: #ccc; }
@media (max-width: 768px) { .movie-item { width: 100%; } }
"""

_FALLBACK_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>{{ styles }}</style>
    <script>function openImage(u){window.open(u,'_blank');}</script>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="container">
    {% for movie in movies %}
    <div class="movie-item">
        <img src='{{ movie.image_url }}' alt='{{ movie.name }}' ondblclick="openImage('{{ movie.image_url }}')">
        <div class="movie-content">
            <div class="movie-title">{{ movie.name }}</div>
            {% set r = movie.rating | float(default=0.0) %}
            {% set w = r * 10 %}
            {% if r >= 8.0 %}{% set fc='fill-high' %}{% set sc='rating-high' %}
            {% elif r >= 7.0 %}{% set fc='fill-mid' %}{% set sc='rating-mid' %}
            {% else %}{% set fc='fill-low' %}{% set sc='rating-low' %}{% endif %}
            <div class="rating-display">
                <div>评分:</div>
                <div class="linear-gauge-container">
                    <div class="linear-gauge-bar {{ fc }}" style="width:{{ w }}%;"></div>
                </div>
                <span style="margin-left:10px;"><span class="rating-score {{ sc }}">{{ movie.rating }}</span></span>
            </div>
            <p class='summary-cn'>{{ movie.summary_cn }}</p>
            <p class='summary-en'>{{ movie.summary_en }}</p>
        </div>
        <div class="counter">{{ loop.index }}</div>
    </div>
    {% endfor %}
    </div>
</body>
</html>"""


def _load_template_and_css(
    template_dir: str,
    html_name: str,
    css_name: str,
) -> tuple[Environment, str, str]:
    """
    加载模板目录中的 HTML 和 CSS。
    返回 (jinja2_env, html_template_name, css_content)。
    失败时抛出 FileNotFoundError。
    """
    html_path = os.path.join(template_dir, html_name)
    css_path  = os.path.join(template_dir, css_name)

    if not os.path.exists(html_path):
        raise FileNotFoundError(f"HTML 模板不存在: {html_path}")

    css_content = ""
    if os.path.exists(css_path):
        with open(css_path, encoding="utf-8") as f:
            css_content = f.read()
        logger.debug(f"✅ 已加载 CSS: {css_path}")
    else:
        logger.warning(f"⚠️ CSS 文件不存在 ({css_path})，样式将为空")

    env = Environment(loader=FileSystemLoader(template_dir))
    return env, html_name, css_content


def generate_html(
    results: list,
    template_dir:  str = _DEFAULT_TEMPLATE_DIR,
    html_name:     str = _DEFAULT_HTML_NAME,
    css_name:      str = _DEFAULT_CSS_NAME,
    output_path:   str = _DEFAULT_OUTPUT_PATH,
    open_browser:  bool = True,
) -> bool:
    """
    从 results 生成 output.html。

    Args:
        results:      [(name, rating, summary_cn, summary_en, image_url), ...]
        template_dir: 模板目录（含 template.html + template.css）
        html_name:    HTML 模板文件名
        css_name:     CSS 文件名
        output_path:  输出文件路径
        open_browser: 生成后是否自动在浏览器打开

    Returns:
        True 表示成功，False 表示失败
    """
    # 整理数据
    movies = [
        {
            "name":       name,
            "rating":     rating,
            "summary_cn": summary_cn,
            "summary_en": summary_en,
            "image_url":  image_url,
        }
        for name, rating, summary_cn, summary_en, image_url in results
    ]

    # 加载模板（失败时使用内置后备模板）
    try:
        env, html_name_used, css_content = _load_template_and_css(
            template_dir, html_name, css_name
        )
        template = env.get_template(html_name_used)
        logger.info(f"✅ 使用模板: {os.path.join(template_dir, html_name_used)}")
    except FileNotFoundError as e:
        logger.warning(f"⚠️ {e}，使用内置后备模板")
        template    = Template(_FALLBACK_HTML)
        css_content = _FALLBACK_CSS

    # 渲染（CSS 内联注入到 {{ styles }} 占位符）
    try:
        html_content = template.render(
            title="🎬 PMDB 热门电影榜单",
            movies=movies,
            styles=css_content,
        )
    except Exception as e:
        logger.error(f"❌ 模板渲染失败: {e}")
        return False

    # 写入输出文件
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"✅ HTML 已生成: {output_path}（{len(movies)} 部电影）")
    except OSError as e:
        logger.error(f"❌ 写入文件失败: {e}")
        return False

    # 自动在浏览器打开
    if open_browser:
        try:
            webbrowser.open("file://" + os.path.realpath(output_path))
        except Exception as e:
            logger.debug(f"浏览器打开失败（非关键错误）: {e}")

    return True
