"""
Django settings module selector.
Loads appropriate settings based on DJANGO_SETTINGS_MODULE environment variable.

Default: config.settings.local (development)
Production: config.settings.production
"""

import os

# Determine which settings to use
ENV = os.environ.get('DJANGO_ENV', 'local')

if ENV == 'production':
    from .production import *  # noqa
else:
    from .local import *  # noqa

