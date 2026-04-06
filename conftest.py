import sys
import os

# 1. Path'leri ayarla
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'webapp/BotBoxWeb')))

# 2. Settings modülünü belirt
os.environ['DJANGO_SETTINGS_MODULE'] = 'BotBoxWeb.settings'

# 3. Settings yüklenmeden önce DB'yi override et
from django.conf import settings

# Settings'i yükle ama setup() henüz çağırma
settings.DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# 4. Şimdi setup() çağır
import django
django.setup()