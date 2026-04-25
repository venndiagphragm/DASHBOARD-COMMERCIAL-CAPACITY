import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")
print("Sys Path:")
for p in sys.path:
    print(p)

try:
    import flask
    print(f"Flask: {flask.__version__} at {flask.__file__}")
except ImportError as e:
    print(f"Flask Import Error: {e}")

try:
    import flask_sqlalchemy
    print(f"Flask-SQLAlchemy: {flask_sqlalchemy.__version__} at {flask_sqlalchemy.__file__}")
except ImportError as e:
    print(f"Flask-SQLAlchemy Import Error: {e}")
