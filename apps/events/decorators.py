import uuid
from functools import wraps

from django.http import Http404


def parse_uuid_param(param_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(self, request, *args, **kwargs):
            try:
                kwargs[param_name] = uuid.UUID(kwargs[param_name])
            except (ValueError, KeyError):
                raise Http404("Invalid UUID for %s" % param_name)
            return view_func(self, request, *args, **kwargs)

        return _wrapped

    return decorator


def with_route_name(name):
    def decorator(view_func):
        def wrapped(self, request, *args, **kwargs):
            request.route_name = name
            return view_func(self, request, *args, **kwargs)

        return wrapped

    return decorator
