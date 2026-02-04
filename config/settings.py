"""
Django settings module selector.
Loads appropriate settings based on environment variables.

Default: config.local (development)
Production: config.production (on Heroku or when DATABASE_URL is set)
"""

import os

# Check if we're on Heroku or if production settings are explicitly requested
if 'DATABASE_URL' in os.environ or os.environ.get('DJANGO_ENV') == 'production':
    from .production import *  # noqa
else:
    from .local import *  # noqa

