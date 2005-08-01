ADMINS = (('Adrian Holovaty','aholovaty@ljworld.com'), ('Jacob Kaplan-Moss', 'jacob@lawrence.com'))
TIME_ZONE = 'America/Chicago'

SERVER_EMAIL = 'root@pam.servers.ljworld.com'
MANAGERS = (('Wilson Miner','wminer@ljworld.com'),)

DEBUG = False
PREPEND_WWW = True

DATABASE_ENGINE = 'postgresql'
DATABASE_NAME = 'djangoproject'
DATABASE_USER = 'apache'
DATABASE_PASSWORD = ''
DATABASE_HOST = '' # set to empty string for localhost

SITE_ID = 1
TEMPLATE_DIRS = (
    '/home/html/templates/djangoproject.com/',
    '/home/html/templates/default/',
)
ROOT_URLCONF = 'django_website.settings.urls.main'
INSTALLED_APPS = (
    'django.contrib.comments',
    'django_website.apps.blog',
    'django_website.apps.docs',
)
MEDIA_ROOT = "/home/html/djangoproject.com/m/"
MEDIA_URL = "http://www.djangoproject.com.com/m/"

# setting for documentation root path
DJANGO_DOCUMENT_ROOT_PATH = "/home/html/djangoproject.com/docs/"
DJANGO_TESTS_PATH = "/home/html/djangoproject.com/docs/tests/"

CACHE_MIDDLEWARE_SECONDS = 60 * 60 * 1 # 1 hour
CACHE_MIDDLEWARE_KEY_PREFIX = 'djangoproject'
CACHE_MIDDLEWARE_GZIP = True

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.middleware.cache.CacheMiddleware",
)
