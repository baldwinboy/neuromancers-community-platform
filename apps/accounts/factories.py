import secrets

import factory
from allauth.account.models import EmailAddress
from allauth.account.signals import user_signed_up
from django.contrib.auth import get_user_model

from .models import UserGroup

User = get_user_model()


@factory.django.mute_signals(user_signed_up)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    username = factory.LazyAttribute(
        lambda o: f"{o.first_name.lower()}_{o.last_name.lower()}_{secrets.token_hex(2)}"
    )
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        """
        Assign existing groups.
        Usage: UserFactory(groups=['SupportSeeker', 'Peer'])
        """
        if not create:
            return

        if extracted:
            for group_name in extracted:
                group = UserGroup.objects.get(name=group_name)
                self.groups.add(group)

    @factory.post_generation
    def verify_email(self, create, extracted, **kwargs):
        """
        Automatically mark the user's primary email as verified.
        """
        if not create:
            return
        # mark the primary email as verified
        EmailAddress.objects.create(
            user=self,
            email=self.email,
            verified=True,
            primary=True,
        )
