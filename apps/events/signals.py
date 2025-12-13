from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from apps.accounts.models import UserGroup
from apps.events.models_sessions.peer import PeerScheduledSession

from .choices import SessionRequestStatusChoices
from .models import GroupSession, GroupSessionRequest, PeerSession, PeerSessionRequest
from .notifications import (
    notify_session_approved,
    notify_session_published,
    notify_session_requested,
)


@receiver(post_save, sender=PeerSession)
def set_peersession_permissions(sender, instance, created, **kwargs):
    """
    - Assigns Support Seeker permissions for Peer Session if it is published
    - Removes Support Seeker permissions for Peer Session if it is not published
    - Adds host permissions for Peer Session if it is created
    - Sends notification when session is published
    """
    if created:
        host = instance.host
        host_perms = [
            "manage_availability",
            "schedule_session",
            "change_peersession",
            "delete_peersession",
            "view_peersession",
        ]

        for perm in host_perms:
            assign_perm(perm, host, instance)

    # Support Seeker group permissions
    try:
        support_seeker_group = UserGroup.objects.get(name="Support Seeker")
    except UserGroup.DoesNotExist:
        return

    seeker_perms = [
        "view_peersession",
        "request_session",
    ]

    if instance.is_published:
        for perm in seeker_perms:
            assign_perm(perm, support_seeker_group, instance)
        # Notify host when session is published
        notify_session_published(instance)
    else:
        for perm in seeker_perms:
            remove_perm(perm, support_seeker_group, instance)


@receiver(post_save, sender=PeerSessionRequest)
def set_peersessionrequest_permissions(sender, instance, created, **kwargs):
    """
    - Assigns approval to the host
    - Assigns withdrawal to the attendee
    - Sends notification when request is created
    - Sends notification when request is approved
    """
    if created:
        assign_perm("approve_peer_request", instance.session.host, instance)
        assign_perm("withdraw_peer_request", instance.attendee, instance)
        # Notify host of new request
        notify_session_requested(instance)
    elif instance.status == SessionRequestStatusChoices.APPROVED:
        # Create scheduled session upon approval
        if not hasattr(instance, "scheduled_session"):
            session = PeerScheduledSession(
                request=instance,
            )
            session.save()

        # Notify attendee that their request was approved
        notify_session_approved(instance)


@receiver(post_save, sender=GroupSession)
def set_groupsession_permissions(sender, instance, created, **kwargs):
    """
    - Assigns Support Seeker permissions for Group Session if it is published
    - Removes Support Seeker permissions for Group Session if it is not published
    - Adds host permissions for Group Session if it is created
    """
    if created:
        # Host permissions
        host = instance.host
        host_perms = [
            "change_groupsession",
            "delete_groupsession",
            "view_groupsession",
        ]

        for perm in host_perms:
            assign_perm(perm, host, instance)

    # Support Seeker group permissions
    try:
        support_seeker_group = UserGroup.objects.get(name="Support Seeker")
    except UserGroup.DoesNotExist:
        return

    seeker_perms = [
        "view_groupsession",
        "request_join_session",
    ]

    if instance.is_published:
        for perm in seeker_perms:
            assign_perm(perm, support_seeker_group, instance)
    else:
        for perm in seeker_perms:
            remove_perm(perm, support_seeker_group, instance)


@receiver(post_save, sender=GroupSessionRequest)
def set_groupsessionrequest_permissions(sender, instance, created, **kwargs):
    """
    Handles:
    - Assign/remove permissions for the Support Seeker group
    - Assign host permissions
    """
    if created:
        assign_perm("approve_group_request", instance.session.host, instance)
        assign_perm("withdraw_group_request", instance.attendee, instance)
        # Notify host of new request
        notify_session_requested(instance)
    elif instance.status == SessionRequestStatusChoices.APPROVED:
        # Notify attendee that their request was approved
        notify_session_approved(instance)
