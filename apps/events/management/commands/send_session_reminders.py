"""
Management command to generate Whereby meeting links and send session reminders.

This should be run as a cron job every hour to:
1. Generate Whereby links for sessions starting within 1 hour
2. Send 1-day reminders for sessions starting in 24 hours
3. Send 1-hour reminders for sessions starting in 1 hour
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import NotificationChoices
from apps.events.choices import SessionRequestStatusChoices
from apps.events.models import GroupSession, PeerSessionRequest
from apps.events.utils import (
    generate_group_meeting_link_if_needed,
    generate_peer_meeting_link_if_needed,
)


class Command(BaseCommand):
    help = "Generate Whereby links and send session reminders"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        now = timezone.now()

        # Time windows
        one_hour_from_now = now + timedelta(hours=1)
        one_hour_window_end = one_hour_from_now + timedelta(minutes=5)  # 5min buffer

        one_day_from_now = now + timedelta(days=1)
        one_day_window_end = one_day_from_now + timedelta(minutes=30)  # 30min buffer

        self.stdout.write(f"Running at {now}")

        # Process session requests
        peer_requests = PeerSessionRequest.objects.filter(
            status=SessionRequestStatusChoices.APPROVED,
            starts_at__gte=now,
            session__is_published=True,
            scheduled_session__meeting_link__isnull=False,
        ).select_related("session", "session__host", "attendee")

        group_sessions = GroupSession.objects.filter(
            is_published=True, starts_at__gte=now, meeting_link__isnull=False
        ).select_related("host", "attendee")

        link_count = 0
        reminder_1h_count = 0
        reminder_1d_count = 0

        for request in peer_requests:
            if dry_run:
                link_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY RUN] Would generate link for {request.session.title}"
                    )
                )
                continue

            link = generate_peer_meeting_link_if_needed(request)
            if not link:
                continue

            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated link for {request.session.title} - {request.attendee.username}"
                )
            )

            if one_hour_from_now <= request.starts_at <= one_hour_window_end:
                # Send 1-hour reminder with link
                self._send_reminder(request, "1_hour", dry_run)
                reminder_1h_count += 1
            elif one_day_from_now <= request.starts_at <= one_day_window_end:
                self._send_reminder(request, "1_day", dry_run)
                reminder_1d_count += 1

        for session in group_sessions:
            if dry_run:
                link_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY RUN] Would generate link for {session.title}"
                    )
                )
                continue

            link = generate_group_meeting_link_if_needed(session)
            if not link:
                continue

            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated link for {session.title} - {session.host.username}"
                )
            )

            if one_hour_from_now <= session.starts_at <= one_hour_window_end:
                # Send 1-hour reminder with link
                self._send_reminder(session, "1_hour", dry_run)
                reminder_1h_count += 1
            elif one_day_from_now <= session.starts_at <= one_day_window_end:
                self._send_reminder(session, "1_day", dry_run)
                reminder_1d_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"  - Whereby links generated: {link_count}\n"
                f"  - 1-hour reminders sent: {reminder_1h_count}\n"
                f"  - 1-day reminders sent: {reminder_1d_count}"
            )
        )

    def _send_reminder(self, request, reminder_type, dry_run=False):
        """Send reminder notification based on user preferences."""
        # Check host preferences
        host = request.session.host
        attendee = request.attendee

        # Get notification settings
        host_settings = (
            host.peer_notification_settings
            if hasattr(host, "peer_notification_settings")
            else host.notification_settings
        )
        attendee_settings = attendee.notification_settings

        # Determine notification preference
        host_pref = host_settings.host_session_reminders
        attendee_pref = attendee_settings.session_reminders

        message = self._build_reminder_message(request, reminder_type)

        if not dry_run:
            # Send to host
            if host_pref in [NotificationChoices.WEB_ONLY, NotificationChoices.ALL]:
                self._create_notification(host, "Session Reminder", message)
            if host_pref in [NotificationChoices.EMAIL, NotificationChoices.ALL]:
                self._send_email(host, "Session Reminder", message)

            # Send to attendee
            if attendee_pref in [NotificationChoices.WEB_ONLY, NotificationChoices.ALL]:
                self._create_notification(attendee, "Session Reminder", message)
            if attendee_pref in [NotificationChoices.EMAIL, NotificationChoices.ALL]:
                self._send_email(attendee, "Session Reminder", message)
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would send {reminder_type} reminder for {request.session.title}"
                )
            )

    def _build_reminder_message(self, request, reminder_type):
        """Build reminder message text."""
        time_text = "1 hour" if reminder_type == "1_hour" else "24 hours"

        message = (
            f"Your session '{request.session.title}' starts in {time_text}.\n\n"
            f"Start time: {request.starts_at.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
            f"Duration: {request.ends_at - request.starts_at}\n"
        )

        if request.meeting_link:
            message += f"\nJoin here: {request.meeting_link}"

        return message

    def _create_notification(self, user, subject, message):
        """Create in-platform notification."""
        from apps.accounts.models import Notifications, NotificationSubjectChoices

        Notifications.objects.create(
            sent_to=user,
            subject=NotificationSubjectChoices.REMINDER,
            body=message,
        )

    def _send_email(self, user, subject, message):
        """Send email notification."""
        from django.conf import settings
        from django.core.mail import send_mail

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
