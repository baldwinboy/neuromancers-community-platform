from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from django.http import HttpRequest

from .models import UserGroup


class AccountAdapter(DefaultAccountAdapter):
    def confirm_email(self, request: HttpRequest, email_address: EmailAddress):
        """
        Default all accounts to support seeker group after account verification
        """
        super().confirm_email(request=request, email_address=email_address)

        support_seeker_group = UserGroup.objects.get(name="Support Seeker")
        email_address.user.groups.add(support_seeker_group)
