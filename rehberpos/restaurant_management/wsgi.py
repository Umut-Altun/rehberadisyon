"""
WSGI config for restaurant_management project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_management.settings')

application = get_wsgi_application()

# Whitenoise ile statik dosya sunumu
try:
    from whitenoise import WhiteNoise
    from django.conf import settings
    application = WhiteNoise(application)
    application.add_files(settings.STATIC_ROOT, prefix="static/")
    
    # Media dosyalarını da sunmak istiyorsanız (geliştirme ortamında)
    if settings.DEBUG:
        application.add_files(settings.MEDIA_ROOT, prefix="media/")
    
    print("WhiteNoise statik dosya sunucusu başlatıldı.")
except ImportError:
    print("WhiteNoise kurulu değil. Statik dosya sunumu için pip install whitenoise çalıştırın.")
except Exception as e:
    print(f"WhiteNoise yüklenirken hata oluştu: {e}")
