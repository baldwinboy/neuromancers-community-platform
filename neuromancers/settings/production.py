from .base import *

ENVIRONMENT = "development"

DEBUG = False

try:
    from .local import *
except ImportError:
    pass
