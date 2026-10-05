"""Settings for running mypy/django-stubs on the host.

Reuses the test settings but defaults ``DATABASE_URL`` to a local SQLite URL, so
the django-stubs plugin can import settings without a Postgres server. mypy
never opens a database connection.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/mypy.sqlite3")

from .test import *  # noqa: F403
