from allauth.account.models import EmailAddress


def create_email_confirmation(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        EmailAddress.objects.create(
            user=instance,
            email=instance.email,
            verified=True,
            primary=True,
        )
