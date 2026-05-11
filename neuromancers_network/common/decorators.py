import uuid
from functools import wraps

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect


def parse_uuid_param(param_name):

    def decorator(view_func):

        @wraps(view_func)
        def _wrapped(self, request, *args, **kwargs):
            try:
                kwargs[param_name] = uuid.UUID(kwargs[param_name])
            except ValueError, KeyError:
                msg = f"Invalid UUID for {param_name}"
                raise Http404(msg) from None
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


def stripe_account_required(view_func):

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        from neuromancers_network.common.stripe import Stripe

        user = request.user

        if not user.stripe_account:
            messages.info(request, "Connect your Stripe account to host sessions")
            return redirect("accounts_user_settings")

        try:
            if not Stripe().is_account_ready(user.stripe_account.id):
                messages.info(request, "Connect your Stripe account to host sessions")
                return redirect("accounts_user_settings")
        except Exception:
            messages.info(request, "Unable to verify Stripe account status")
            return redirect("accounts_user_settings")

        return view_func(request, *args, **kwargs)

    return _wrapped
