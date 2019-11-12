"""
Django settings for maas_experiment project.

Generated by 'django-admin startproject' using Django 2.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY",'cm_v*vc*8s048%f46*@t7)hb9rtaa@%)#b!s(+$4+iw^tjt=s6')

# Since 'MAAS_PORTAL_DEBUG' will be a string, we have no guarrentee that it is a boolean.
debug_setting = os.environ.get('MAAS_PORTAL_DEBUG', True)

# This is a list of strings that might be considered as False
false_options = ['false', '0', 'f', 'no']

# If the debug setting came in as a string instead of a boolean, only set it as False if the input
# could be considered as False
if type(debug_setting) is not bool:
    debug_setting = debug_setting.lower() not in false_options

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = debug_setting

# Must be set in production!
ALLOWED_HOSTS = ['*']

# The default is false; if it's not true, it will leave a user logged in indefinitely
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# This is the absolute age; navigating won't necessarily tell the system that anything is happening
# and sessions will absolutely end after this time, regardless of what is going on.
# In this case, you will be logged off after 5 minutes even if you were actively working.
# SESSION_COOKIE_AGE = 300

# security.W007: Activate's the browser's XSS filtering to help prevent XSS attacks
SECURE_BROWSER_XSS_FILTER = True

# Only enable the following settings if this instance was run with the DEPLOYED variable
deployed_setting = os.environ.get('DEPLOYED', False)

if type(deployed_setting) is not bool:
    deployed_setting = deployed_setting.lower() not in false_options

# Whether to use a secure cookie for the session cookie. If this is set to True, the cookie will be marked as
# “secure”, which means browsers may ensure that the cookie is only sent under an HTTPS connection.
# Leaving this setting off isn’t a good idea because an attacker could capture an unencrypted session cookie with a
# packet sniffer and use the cookie to hijack the user’s session.
SESSION_COOKIE_SECURE = deployed_setting

# Whether to use a secure cookie for the CSRF cookie. If this is set to True, the cookie will be marked as “secure”,
# which means browsers may ensure that the cookie is only sent with an HTTPS connection.
CSRF_COOKIE_SECURE = deployed_setting

# Whether to use HttpOnly flag on the CSRF cookie. If this is set to True, client-side JavaScript will not be able
# to access the CSRF cookie.
# Designating the CSRF cookie as HttpOnly doesn’t offer any practical protection because CSRF is only to protect
# against cross-domain attacks. If an attacker can read the cookie via JavaScript, they’re already on the same
# domain as far as the browser knows, so they can do anything they like anyway. (XSS is a much bigger hole than CSRF.)
#
# Although the setting offers little practical benefit, it’s sometimes required by security auditors.
CSRF_COOKIE_HTTPONLY = deployed_setting

# Whether to store the CSRF token in the user’s session instead of in a cookie.
# It requires the use of django.contrib.sessions.
#
# Storing the CSRF token in a cookie (Django’s default) is safe, but storing it in the session is common practice
# in other web frameworks and therefore sometimes demanded by security auditors.
CSRF_USE_SESSIONS = deployed_setting

# security.W019: Unless we start serving data in a frame, set to 'DENY'
X_FRAME_OPTIONS = 'DENY'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'MaaS.apps.MaasConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'maas_experiment.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'maas_experiment.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ.get("MAAS_TIMEZONE", 'UTC')

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static/")
