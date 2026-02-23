#!/usr/bin/env python3
"""
Convert Django templates to static HTML for GitHub Pages
"""
import re
import sys

def convert_django_to_static(template_path, output_path, title="OWASP GSoC"):
    """Convert Django template to static HTML"""
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # First, extract the content between {% block content %} and {% endblock %}
    content_match = re.search(r'{%\s*block\s+content\s*%}(.*?){%\s*endblock', content, re.DOTALL)
    if content_match:
        content = content_match.group(1)
    
    # Extract extra_head styles if present
    style_match = re.search(r'{%\s*block\s+extra_head\s*%}(.*?){%\s*endblock', content, re.DOTALL)
    extra_styles = style_match.group(1) if style_match else ""
    
    # Remove Django template tags
    content = re.sub(r'{%\s*extends\s+["\'].*?["\']\s*%}', '', content)
    content = re.sub(r'{%\s*load\s+.*?%}', '', content)
    content = re.sub(r'{%\s*block\s+.*?%}', '', content)
    content = re.sub(r'{%\s*endblock.*?%}', '', content)
    content = re.sub(r'{%\s*include\s+["\'].*?["\']\s*%}', '<!-- Removed sidenav -->', content)
    
    # Replace {% static %} tags with relative paths
    content = re.sub(r'{%\s*static\s+["\']images/([^"\']+)["\']\s*%}', r'images/\1', content)
    content = re.sub(r'{%\s*static\s+["\']js/([^"\']+)["\']\s*%}', r'js/\1', content)
    content = re.sub(r'{%\s*static\s+["\']css/([^"\']+)["\']\s*%}', r'css/\1', content)
    content = re.sub(r'{%\s*static\s+["\']([^"\']+)["\']\s*%}', r'\1', content)
    
    # Remove any remaining Django tags
    content = re.sub(r'{%.*?%}', '', content)
    content = re.sub(r'{{.*?}}', '', content)
    
    # Clean up extra whitespace
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    # Create full HTML document
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Join the Google Summer of Code program with OWASP and contribute to open source security projects.">
    <meta name="keywords" content="GSoC, Google Summer of Code, OWASP, Open Source, Student Program, Mentorship">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="Learn about the Google Summer of Code (GSoC) program and its partnership with OWASP.">
    <meta property="og:type" content="website">
    
    <title>{title}</title>
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Custom Styles -->
    <link rel="stylesheet" href="css/main.css">
    
    {extra_styles}
</head>
<body class="bg-white dark:bg-gray-900">
    <!-- Navigation -->
    <nav class="bg-white dark:bg-gray-800 shadow-md">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <h1 class="text-xl font-bold text-gray-900 dark:text-white">OWASP BLT GSoC</h1>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="index.html" class="text-gray-700 dark:text-gray-300 hover:text-red-500">Home</a>
                    <a href="pr-report.html" class="text-gray-700 dark:text-gray-300 hover:text-red-500">PR Analytics</a>
                    <a href="https://github.com/OWASP-BLT/BLT-GSOC" class="text-gray-700 dark:text-gray-300 hover:text-red-500">
                        <i class="fab fa-github"></i> GitHub
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
{content}

    <!-- Footer -->
    <footer class="bg-gray-100 dark:bg-gray-800 mt-20">
        <div class="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div class="text-center">
                <p class="text-gray-600 dark:text-gray-400">
                    © 2024-2026 OWASP Foundation. Part of the 
                    <a href="https://github.com/OWASP-BLT/BLT" class="text-red-500 hover:text-red-600">OWASP BLT Project</a>
                </p>
                <p class="text-gray-500 dark:text-gray-500 mt-2 text-sm">
                    Hosted on <a href="https://pages.github.com/" class="text-red-500 hover:text-red-600">GitHub Pages</a>
                </p>
            </div>
        </div>
    </footer>
</body>
</html>'''
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✓ Converted {template_path} to {output_path}")

if __name__ == "__main__":
    # Convert main GSoC page
    convert_django_to_static(
        'templates/gsoc.html',
        'docs/index.html',
        'Google Summer of Code with OWASP'
    )
    
    print("\n✓ Conversion complete!")
