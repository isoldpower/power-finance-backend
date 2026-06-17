"""Test bootstrap for the correlation-py library.

The library targets Django but is not itself a Django app, so tests run
against a minimal `settings.configure()` rather than a real project.
Importing this package side-effect-configures Django on first use.
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        DATABASES={},
        INSTALLED_APPS=[],
        SECRET_KEY="test-secret-key",
        USE_TZ=True,
    )
    django.setup()
