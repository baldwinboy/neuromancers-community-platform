from django.db import migrations
from django.db import models
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.functions import Trim


def _preflight_no_case_collisions(User, EmailAddress, db_alias):
    duplicate_usernames = (
        User.objects.using(db_alias)
        .annotate(canonical=Lower(Trim("username")))
        .values("canonical")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    if duplicate_usernames.exists():
        raise RuntimeError(
            "Cannot normalise identities: case-insensitive duplicate usernames "
            "exist. Resolve them before migrating.",
        )

    duplicate_emails = (
        User.objects.using(db_alias)
        .exclude(email="")
        .annotate(canonical=Lower(Trim("email")))
        .values("canonical")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    if duplicate_emails.exists():
        raise RuntimeError(
            "Cannot normalise identities: case-insensitive duplicate user "
            "emails exist. Resolve them before migrating.",
        )

    duplicate_addresses_per_user = (
        EmailAddress.objects.using(db_alias)
        .annotate(canonical=Lower(Trim("email")))
        .values("user_id", "canonical")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    if duplicate_addresses_per_user.exists():
        raise RuntimeError(
            "Cannot normalise identities: case-insensitive duplicate "
            "EmailAddress rows exist for the same user. Resolve them before "
            "migrating.",
        )

    duplicate_verified_addresses = (
        EmailAddress.objects.using(db_alias)
        .filter(verified=True)
        .annotate(canonical=Lower(Trim("email")))
        .values("canonical")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    if duplicate_verified_addresses.exists():
        raise RuntimeError(
            "Cannot normalise identities: case-insensitive duplicate verified "
            "EmailAddress rows exist. Resolve them before migrating.",
        )


def normalise_identities(apps, schema_editor):
    """Lowercase identities and backfill allauth address rows.

    This migration intentionally fails rather than picking a winner when
    case-insensitive duplicates exist. The casing rewrite is irreversible.
    """
    db_alias = schema_editor.connection.alias
    User = apps.get_model("users", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")

    _preflight_no_case_collisions(User, EmailAddress, db_alias)

    User.objects.using(db_alias).update(
        username=Lower(Trim("username")),
        email=Lower(Trim("email")),
    )
    EmailAddress.objects.using(db_alias).update(
        email=Lower(Trim("email")),
    )

    for user in User.objects.using(db_alias).exclude(email="").iterator():
        email = user.email
        address = (
            EmailAddress.objects.using(db_alias)
            .filter(user_id=user.pk, email=email)
            .first()
        )
        if address is None:
            address = EmailAddress.objects.using(db_alias).create(
                user_id=user.pk,
                email=email,
                verified=False,
                primary=False,
            )

        EmailAddress.objects.using(db_alias).filter(
            user_id=user.pk,
            primary=True,
        ).exclude(pk=address.pk).update(primary=False)

        if not address.primary:
            address.primary = True
            address.save(update_fields=["primary"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_alter_profileeditformpage_body"),
        ("account", "0009_emailaddress_unique_primary_email"),
    ]

    operations = [
        migrations.RunPython(
            normalise_identities,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                Lower("username"),
                name="users_user_username_ci_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                Lower("email"),
                condition=~Q(email=""),
                name="users_user_email_ci_unique",
            ),
        ),
    ]
