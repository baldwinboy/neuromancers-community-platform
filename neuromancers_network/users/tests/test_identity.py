import pytest
from allauth.account.models import EmailAddress
from django.db import IntegrityError
from django.db import transaction

from neuromancers_network.moderation.services import purge_account
from neuromancers_network.users.models import User
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_save_normalises_identity_without_update_fields():
    user = UserFactory(username="Original", email="Original@Example.COM")

    assert user.username == "original"
    assert user.email == "original@example.com"

    user.username = "Changed"
    user.email = "Changed@Example.COM"
    user.save()

    user.refresh_from_db()
    assert user.username == "changed"
    assert user.email == "changed@example.com"


def test_user_save_normalises_identity_with_update_fields():
    user = UserFactory(username="original", email="original@example.com")
    user.username = "Changed"

    user.save(update_fields=["username"])

    user.refresh_from_db()
    assert user.username == "changed"
    assert user.email == "original@example.com"


def test_user_factory_is_case_insensitive_when_idempotent():
    first = UserFactory(username="MixedCase")
    second = UserFactory(username="mixedcase")

    assert second.pk == first.pk
    assert second.username == "mixedcase"


def test_username_uniqueness_is_case_insensitive():
    UserFactory(username="Foo")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(username="foo", email="other@example.com")


def test_email_uniqueness_is_case_insensitive():
    UserFactory(email="A@Example.COM")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(username="other", email="a@example.com")


def test_blank_emails_do_not_collide():
    first = UserFactory(email="")
    second = UserFactory(email="")

    assert first.email == ""
    assert second.email == ""


def test_email_address_save_normalises_address():
    user = UserFactory()
    address = EmailAddress.objects.create(
        user=user,
        email="Mixed@Example.COM",
        primary=True,
        verified=True,
    )

    address.refresh_from_db()
    assert address.email == "mixed@example.com"


def test_direct_user_email_save_syncs_email_address():
    user = UserFactory(email="old@example.com")
    EmailAddress.objects.create(
        user=user,
        email="old@example.com",
        primary=True,
        verified=True,
    )

    user.email = "New@Example.COM"
    user.save()

    user.refresh_from_db()
    assert user.email == "new@example.com"
    assert (
        EmailAddress.objects.get(
            user=user,
            email="new@example.com",
        ).primary
        is True
    )
    assert (
        EmailAddress.objects.get(
            user=user,
            email="old@example.com",
        ).primary
        is False
    )


def test_purge_does_not_create_tombstone_email_address():
    user = UserFactory(email="member@example.com")
    EmailAddress.objects.create(
        user=user,
        email="member@example.com",
        primary=True,
        verified=True,
    )

    purge_account(user)

    assert not EmailAddress.objects.filter(
        user=user,
        email__endswith="@deleted.invalid",
    ).exists()
