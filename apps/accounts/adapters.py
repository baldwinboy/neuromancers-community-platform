from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.utils import import_attribute
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    def confirm_email(self, request: HttpRequest, email_address: EmailAddress):
        """
        Default all accounts to support seeker group after account verification
        """
        super().confirm_email(request=request, email_address=email_address)

        user_groups = import_attribute(settings.USER_GROUPS)

        if not isinstance(user_groups, tuple):
            raise ImproperlyConfigured("USER_GROUPS is expected to be a tuple")

        support_seeker_group_name = user_groups.SUPPORT_SEEKER

        if not support_seeker_group_name:
            raise ImproperlyConfigured("USER_GROUPS is expected to have SUPPORT_SEEKER")

        support_seeker_group = Group.objects.get(name=support_seeker_group_name)
        email_address.user.groups.add(support_seeker_group)
