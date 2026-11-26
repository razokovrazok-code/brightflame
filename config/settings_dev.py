"""
Development settings using SQLite (no PostgreSQL required).
Usage: python manage.py runserver --settings=config.settings_dev
"""
from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_dev.sqlite3',  # noqa: F405
    }
}

DEBUG = True
SECRET_KEY = 'dev-secret-key-wms-2024-change-in-production-minimum-50-chars-xyz'
ALLOWED_HOSTS = ['*']

# Disable whitenoise manifest for dev
STORAGES = {
    **STORAGES,  # noqa: F405
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
