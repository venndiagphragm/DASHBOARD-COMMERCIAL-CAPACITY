import glob
import re

html_files = glob.glob('templates/*.html')

new_nav = """<div class="hamburger" id="hamburger-menu">
                <div></div>
                <div></div>
                <div></div>
            </div>
            <nav class="popup-nav-container" id="main-nav">
                <ul class="nav-tiles-grid">
                    <li class="nav-tile-item"><a href="{{ url_for('index') }}" class="{% if request.endpoint == 'index' %}active{% endif %}">Home</a></li>
                    <li class="nav-tile-item"><a href="{{ url_for('profile') }}">Company Profile</a></li>
                    <li class="nav-tile-item"><a href="{{ url_for('pricing_map') }}">Peta & Tarif</a></li>
                    {% if current_user.is_authenticated %}
                    <li class="nav-tile-item"><a href="{{ url_for('dashboard') }}">Dashboard</a></li>
                    <li class="nav-tile-item"><a href="{{ url_for('insights') }}">Insights</a></li>
                    <li class="nav-tile-item"><a href="{{ url_for('input_data') }}">Input Data</a></li>
                    <li class="nav-tile-item logout-tile" style="grid-column: span 2;"><a href="{{ url_for('logout') }}">Logout</a></li>
                    {% else %}
                    <li class="nav-tile-item login-tile" style="grid-column: span 2;"><a href="{{ url_for('login') }}">Login</a></li>
                    {% endif %}
                </ul>
            </nav>
            <script>
                document.getElementById('hamburger-menu').addEventListener('click', function() {
                    this.classList.toggle('active');
                    const nav = document.getElementById('main-nav');
                    nav.classList.toggle('active');
                });
            </script>"""

for file in html_files:
    if 'login.html' in file: continue
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    # It replaces the previously injected hamburger to script closing tag.
    new_content = re.sub(r'<div class="hamburger".*?</script>', new_nav, content, flags=re.DOTALL)
    with open(file, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
print("Nav tiles injected successfully.")
