from jinja2 import Template, Environment, FileSystemLoader
import os
import webbrowser

def get_default_template():
    """Returns the default HTML template string (fallback if template.html is missing)."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        .container { display: flex; flex-wrap: wrap; justify-content: space-between; }
        .movie-item { width: 48%; margin-bottom: 20px; overflow: hidden; border: 1px solid black; padding: 10px; }
        img { max-width: 150px; height: auto; margin-right: 10px; float: left; cursor: pointer; }
        .rating { color: red; font-weight: bold; }
        .summary-cn { color: blue; }
        .summary-en { color: black; }
    </style>
    <script>
        function openImage(url) { window.open(url, '_blank'); }
    </script>
</head>
<body>
    <h1>{{ title }}</h1>
    <div class="container">
        {% for movie in movies %}
        <div class="movie-item">
            <img src='{{ movie.image_url }}' alt='{{ movie.name }}' ondblclick="openImage('{{ movie.image_url }}')">
            <strong>{{ movie.name }}</strong> — Rating: <span class='rating'>{{ movie.rating }}</span><br>
            <p><span class='summary-cn'>{{ movie.summary_cn }}</span><br>
            <span class='summary-en'>{{ movie.summary_en }}</span></p>
        </div>
        {% endfor %}
    </div>
</body>
</html>"""

def generate_html(results, template_path="template.html", output_path="output.html"):
    """
    Generate HTML file using Jinja2 template.
    """
    try:
        # Prepare template data
        movies = []
        for name, rating, summary_cn, summary_en, image_url in results:
            movies.append({
                'name': name,
                'rating': rating,
                'summary_cn': summary_cn,
                'summary_en': summary_en,
                'image_url': image_url
            })
        
        # Load template file
        if os.path.exists(template_path):
            template_dir = os.path.dirname(template_path) or '.'
            template_name = os.path.basename(template_path)
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_name)
        else:
            print(f"⚠️ Template file '{template_path}' not found, using default template")
            template = Template(get_default_template())
        
        # Render template
        html_content = template.render(
            title="Movie Information",
            movies=movies
        )
        
        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"✅ HTML file generated: {output_path}")
        
        webbrowser.open('file://' + os.path.realpath(output_path))
        
    except Exception as e:
        print(f"❌ Error generating HTML: {e}")
