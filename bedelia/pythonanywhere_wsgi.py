# This file is for PythonAnywhere deployment
# Place this at: /var/www/yourusername_pythonanywhere_com_wsgi.py

import sys
import os

# Add your project directory to the Python path
project_home = '/home/yourusername/bedelia'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# Import Django's WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

