Notifications: Inbox Event Bus and daisIE Email Bridges
======================================================================

NEUROMANCERS records every business event that may warrant a notification in a
durable, queryable store — the **event store** — through a small internal
**event bus**. Delivery to members is handled by a concrete subscriber that
forwards events to admin-authored daisIE ``EmailTemplate`` s.

The pipeline is::

    domain signal -> inbox.events.emit() -> NotificationEventLog (durable)
                                            -> active EventSubscribers
                                               -> DaisieBridgeSubscriber
                                                  -> wagtail_daisIE dispatch()
                                                     -> EmailTemplate rendered + sent

The event types
---------------------------------------------------------------------

The canonical, closed set of events lives in ``NotificationEventType``
(``neuromancers_network/inbox/models/event_type.py``). The full list is:

* **Bookings:** ``booking_requested``, ``booking_approved``,
  ``booking_rejected``, ``booking_paid``, ``booking_completed``,
  ``booking_cancelled``.
* **Refunds:** ``refund_requested``, ``refund_approved``,
  ``refund_rejected``, ``refund_refunded``.
* **Reviews:** ``review_created``, ``review_pending_approval``,
  ``review_published``, ``review_hidden`` (peer approval/hide transitions).
* **Peers:** ``peer_approved``, ``peer_application_approved``,
  ``peer_application_rejected``.
* **Subscriptions:** ``subscription_created``, ``subscription_cancelled``,
  ``subscription_paused``, ``subscription_resumed``.
* **Meetings and reminders:** ``meeting_upcoming``, ``meeting_cancelled``,
  ``meeting_unpublished``, ``meetings_unpublished``, ``meetings_deleted``,
  ``session_reminder_1d``, ``session_reminder_1h``, ``payment_reminder_due``.
* **Accounts and identity:** ``account_created``, ``account_deleted``,
  ``account_degraded``, ``account_deactivated``, ``account_reactivated``,
  ``account_deletion_scheduled``, ``account_deletion_cancelled``,
  ``email_changed``, ``username_changed``.
* **Safety and moderation:** ``user_blocked``, ``user_unblocked``,
  ``ip_banned``, ``ip_unbanned``, ``email_banned``, ``email_unbanned``,
  ``report_created``, ``report_resolved``, ``report_rejected``.
* **Privacy, publishing and payments:** ``data_export_requested``,
  ``data_export_ready``, ``peer_published_meeting``, ``payment_succeeded``,
  ``payment_failed``.

The ``account_deletion_scheduled`` payload includes
``meta.deletion_cancel_url``. Include that value in the corresponding
``EmailTemplate`` so members can cancel from the email. Admins can resend the
link from the account-deletion request admin.

How events get recorded
---------------------------------------------------------------------

Signal receivers live in ``neuromancers_network/inbox/signals.py`` (domain
models), ``neuromancers_network/users/signals.py`` (account lifecycle) and
emit through the bus:

.. code-block:: python

   from neuromancers_network.inbox.events import emit

   emit(
       "booking_approved",
       payload={
           "actor_user_id": peer.pk,
           "recipient_user_ids": [seeker.pk],
           "object_type": "meetingrequest",
           "object_id": request.pk,
           "meta": {"meeting_title": meeting.title, "status": request.status},
       },
       event_ref=f"meetingrequest.{request.pk}.approve",
   )

``emit`` appends a row to ``NotificationEventLog`` (the store) and then hands the
row to every matching subscriber. ``event_ref`` is an optional stable key used to
keep scheduled emissions idempotent. Receivers are failure-isolated: problems are
logged, never raised, so the bus cannot break the flow that caused the event.

Subscribing from Wagtail
---------------------------------------------------------------------

``EventSubscriber`` (``neuromancers_network/inbox/models/subscriber.py``) is an
abstract base for Wagtail-instantiable subscribers. The shipped concrete
subclass is ``DaisieBridgeSubscriber`` (``inbox/models/daisie_bridge.py``),
registered as a snippet: create one per ``event_type``, tick ``is_active``, and
each matching event is forwarded to the daisIE bridge system.

Per-member opt-out
---------------------------------------------------------------------

* ``NotificationPreference`` stores a member's ``disabled_event_types``.
* ``NotificationSettings`` holds admin-level ``default_disabled_event_types``
  and ``transactional_events``.
* ``inbox.services.should_notify(user, event_type)`` decides delivery.
  Transactional events (``account_*``, ``booking_paid``, refunds, payments,
  subscriptions) are always delivered.

The shared bridge builders in ``inbox/bridges.py``
(``context_from_payload`` / ``recipients_from_payload``) expose the payload to
the template and resolve only the opted-in recipients.

Configuring email content
---------------------------------------------------------------------

Map each event key to an ``EmailTemplate`` in ``WAGTAIL_DAISIE_NOTIFICATION_BRIDGES``
(``config/settings/base.py``). ``template`` matches an ``EmailTemplate`` by name
or ``template_key``; templates and bridge snippets are created in the Wagtail
admin (no seed data). ``WAGTAIL_DAISIE_NOTIFICATION_FROM_EMAIL`` sets the
envelope sender.

Session emails include booking, session, access-needs, terms and meeting-link
values via ``inbox.payloads.session_payload`` (including an ``ics_url`` for the
member's read-only calendar feed).

Scheduled (time-based) events
---------------------------------------------------------------------

Celery beat tasks in ``neuromancers_network/inbox/tasks.py`` emit time-based
events and are idempotent:

* ``emit_payment_reminders`` — ``payment_reminder_due`` for stale
  ``pending_payment`` bookings.
* ``emit_upcoming_meetings`` — ``meeting_upcoming`` for meetings starting soon.
* ``emit_session_reminders`` — ``session_reminder_1d`` / ``session_reminder_1h``.

Administration
---------------------------------------------------------------------

* Operations → **Notification preferences** manages per-member opt-outs
  with a flat checkbox list of event types (no raw JSON).
* Settings → **Notification Settings** and Settings → **Email Settings** use
  the same checkbox lists for the admin-level defaults and the test-email
  panel (``/cms/email/test/``).

Where the tests cover this
---------------------------------------------------------------------

See ``neuromancers_network/inbox/tests/``: ``test_event_store.py``,
``test_bus_dispatch.py``, ``test_signals.py``, ``test_tasks.py`` and
``test_session_reminders.py``.
