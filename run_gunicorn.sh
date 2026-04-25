#!/bin/bash
# Install requirements if gunicorn is missing
if ! pip freeze | grep -q "gunicorn"; then
    echo "Installing Gunicorn..."
    pip install gunicorn
fi

# Run Gunicorn
# -w 4: 4 worker processes
# -b 0.0.0.0:5001: Bind to port 5001
# app:app : Module 'app' (app.py) object 'app' (Flask instance)
echo "Starting Gunicorn on port 5001..."
exec gunicorn -w 4 -b 0.0.0.0:5001 app:app
