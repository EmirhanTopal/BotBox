import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'webapp')))

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BotBoxWeb.settings')
os.environ.setdefault('TESTING', '1')

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'chat',
        ],
        DEFAULT_AUTO_FIELD='django.db.backends.BigAutoField',
    )
    django.setup()