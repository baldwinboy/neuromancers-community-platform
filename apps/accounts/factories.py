import secrets

import factory
from allauth.account.models import EmailAddress
from allauth.account.signals import user_signed_up
from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, post_save
from model_bakery import baker

from apps.accounts.defaults import DEFAULT_PEER_NOTIFICATION_SETTINGS

from .models import NotificationSettings, PeerNotificationSettings, Profile, UserGroup

User = get_user_model()


@factory.django.mute_signals(post_save)
class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory("accounts.factories.UserFactory", profile=None)


@factory.django.mute_signals(post_save)
class NotificationSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationSettings

    user = factory.SubFactory(
        "accounts.factories.UserFactory", notification_settings=None
    )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return baker.make(model_class, **kwargs)


@factory.django.mute_signals(user_signed_up, post_save, m2m_changed)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    username = factory.LazyAttribute(
        lambda o: f"{o.first_name.lower()}_{o.last_name.lower()}_{secrets.token_hex(2)}"
    )
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "NeuroMancers987!")

    profile = factory.RelatedFactory(
        ProfileFactory,
        factory_related_name="user",
    )

    notification_settings = factory.RelatedFactory(
        NotificationSettingsFactory,
        factory_related_name="user",
    )

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

                if group_name == "Peer":
                    PeerNotificationSettings.objects.create(
                        user=self, **DEFAULT_PEER_NOTIFICATION_SETTINGS
                    )

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
