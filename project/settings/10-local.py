# -*- encoding: utf-8 -*

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

SECRET_KEY = 'ilseraitsagedemodifiercetteclefpourquelquechosedautre.'

RAVEN_CONFIG = {
    'dsn': '',
}

SAML_AUTH = False

# Optionnel
PIWIK_TOKEN = None

DEBUG = True
