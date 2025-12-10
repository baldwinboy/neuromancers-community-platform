from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.accounts.defaults import (
    DEFAULT_NOTIFICATION_SETTINGS,
    DEFAULT_PEER_NOTIFICATION_SETTINGS,
)

from .models import (
    Certificate,
    NotificationSettings,
    PeerFilterSettings,
    PeerNotificationSettings,
    Profile,
    StripeAccount,
    UserGroup,
)

User = get_user_model()

PEER_GROUP_NAME = "Peer"


@receiver(post_save, sender=User)
def create_universal_user_objects(sender, instance, created, **kwargs):
    if not created:
        return

    # Create defaults for all users
    NotificationSettings.objects.create(user=instance, **DEFAULT_NOTIFICATION_SETTINGS)
    Profile.objects.create(user=instance)


@receiver(m2m_changed, sender=User.groups.through)
def handle_peer_group_membership(sender, instance, action, pk_set, **kwargs):
    """
    Triggered whenever a user is added/removed from groups.
    """
    try:
        peer_group = UserGroup.objects.get(name=PEER_GROUP_NAME)
    except UserGroup.DoesNotExist:
        return

    if action in ("post_add"):
        if peer_group.id in pk_set:
            # Create objects if they don't exist
            PeerNotificationSettings.objects.get_or_create(
                user=instance, defaults=DEFAULT_PEER_NOTIFICATION_SETTINGS
            )
            PeerFilterSettings.objects.get_or_create(user=instance)

    if action in ("post_remove"):
        if peer_group.id in pk_set:
            PeerNotificationSettings.objects.filter(user=instance).delete()
            PeerFilterSettings.objects.filter(user=instance).delete()
            Certificate.objects.filter(user=instance).delete()
            StripeAccount.objects.filter(user=instance).delete()
