import os
import glob
import re

html_files = glob.glob('templates/*.html')

new_nav = """<div class="hamburger" id="hamburger-menu" style="cursor: pointer; display: flex; flex-direction: column; gap: 5px; margin-left: auto;">
                <div style="width: 25px; height: 3px; background-color: var(--primary-blue, #1A428A);"></div>
                <div style="width: 25px; height: 3px; background-color: var(--primary-blue, #1A428A);"></div>
                <div style="width: 25px; height: 3px; background-color: var(--primary-blue, #1A428A);"></div>
            </div>
            <nav class="main-nav" id="main-nav" style="display: none; position: absolute; top: 60px; right: 20px; background: white; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-radius: 8px; z-index: 1000;">
                <ul style="display: flex; flex-direction: column; gap: 15px; margin: 0; padding: 0; list-style: none;">
                    <li><a href="{{ url_for('index') }}">Home</a></li>
                    <li><a href="{{ url_for('profile') }}">Company Profile</a></li>
                    <li><a href="{{ url_for('pricing_map') }}">Peta & Tarif</a></li>
                    {% if current_user.is_authenticated %}
                    <li><a href="{{ url_for('dashboard') }}">Dashboard</a></li>
                    <li><a href="{{ url_for('insights') }}">Insights</a></li>
                    <li><a href="{{ url_for('input_data') }}">Input Data</a></li>
                    <li><a href="{{ url_for('logout') }}" style="color: #E53935; font-weight: bold; text-decoration: none;">Logout</a></li>
                    {% else %}
                    <li><a href="{{ url_for('login') }}" style="background: var(--primary-blue, #1A428A); color: white; padding: 8px 15px; border-radius: 4px; text-decoration: none;">Login</a></li>
                    {% endif %}
                </ul>
            </nav>
            <script>
                document.getElementById('hamburger-menu').addEventListener('click', function() {
                    const nav = document.getElementById('main-nav');
                    if (nav.style.display === 'none') {
                        nav.style.display = 'block';
                    } else {
                        nav.style.display = 'none';
                    }
                });
            </script>"""

for file in html_files:
    if 'login.html' in file: continue
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = re.sub(r'<nav class="main-nav">.*?</nav>', new_nav, content, flags=re.DOTALL)
    with open(file, 'w', encoding='utf-8') as f:
        f.write(new_content)
print("Nav replaced!")

try:
    from app import app, db, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        db.create_all()
        if User.query.filter_by(username='admin').first() is None:
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('password'),
                role='company_user'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user seeded.")
except Exception as e:
    print(f"Error seeding user: {e}")
