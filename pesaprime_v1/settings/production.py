"""
Production settings for Vercel deployment
"""

import os
from pathlib import Path
import dj_database_url
from .base import *
from pesaprime_v1.settings import BASE_DIR, MIDDLEWARE

# Vercel deployment
VERCEL = os.environ.get('VERCEL', 'False') == 'True'

if VERCEL:
    # Vercel-specific settings
    DEBUG = False
    ALLOWED_HOSTS = ['.vercel.app', '.now.sh']
    
    # Database configuration for Vercel
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True
        )
    }
    
    # Static files (WhiteNoise)
    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, 'static'),
    ]
    
    # WhiteNoise configuration
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    
    # Middleware with WhiteNoise
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    
    # Media files - use S3 or similar in production
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Security settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # CSRF trusted origins
    CSRF_TRUSTED_ORIGINS = [
        'https://pesaprime2026.vercel.app',
        'https://*.now.sh',
    ]
    
    # CORS settings
    CORS_ALLOWED_ORIGINS = [
        'https://pesaprime2026.vercel.app',
        'https://*.now.sh',
    ]
    CORS_ALLOW_CREDENTIALS = True
    
    # Cache for production
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    
    # Email configuration (use environment variables)
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)