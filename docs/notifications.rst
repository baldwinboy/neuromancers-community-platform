Notifications: Event Bus and Event Store
======================================================================

NEUROMANCERS has no user-facing notification channels yet. Instead, the platform
records every business event that may warrant a notification in a durable,
queryable store — the **event store** — through a small internal **event bus**.

The idea is that a future notification layer (and, eventually, Wagtail-admin
configured channels with templated copy) will be *subscribers* on this bus:
they declare which event type they care about, and the bus calls them whenever
the matching event is recorded. This module is backend-only; no email/SMS/in-app
message is sent today.

The event types
---------------------------------------------------------------------

The canonical, closed set of events lives in
``NotificationEventType`` (``neuromancers_network/notifications/models/event_type.py``):

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Event
     - Meaning
   * - ``booking_requested`` / ``approved`` / ``rejected`` / ``paid`` / ``completed`` / ``cancelled``
     - A ``MeetingRequest`` was created or moved to that FSM state.
   * - ``refund_requested`` / ``approved`` / ``rejected`` / ``refunded``
     - A ``RefundRequest`` was created or moved to that FSM state.
   * - ``review_created``
     - A ``Review`` was created.
   * - ``peer_approved``
     - A ``PeerProfile`` became approved.
   * - ``peer_application_approved`` / ``rejected``
     - A ``PeerApplication`` was decided.
   * - ``subscription_created`` / ``cancelled``
     - A peer subscription started, or its Stripe subscription was cancelled.
   * - ``payment_reminder_due``
     - Emitted periodically for bookings stuck in ``pending_payment``.
   * - ``meeting_upcoming`` / ``cancelled``
     - A meeting starts soon, or a published meeting was archived (cancelled).

How events get recorded
---------------------------------------------------------------------

Domain code (or the signal receivers in ``signals.py``) calls the bus:

.. code-block:: python

   from neuromancers_network.notifications.events import emit

   log_entry = emit(
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

``emit`` appends a row to ``NotificationEventLog`` (the store) and then hands
the row to every matching subscriber. ``event_ref`` is an optional stable key
used to keep scheduled emissions idempotent.

Receivers are deliberately failure-isolated: a problem while recording or
dispatching is logged and never raised, so the event bus cannot break the
booking/refund flow that caused the event.

Subscribing from Wagtail
---------------------------------------------------------------------

``EventSubscriber`` (:mod:`neuromancers_network.notifications.models`) is an
**abstract** base for Wagtail-instantiable subscribers. A concrete subclass
declares which ``event_type`` it listens to and an ``is_active`` switch; every
active instance whose event fires receives a call to ``handle_event(log_entry)``.

Concrete subclasses are registered automatically with the bus the moment they
are defined. No concrete subscriber ships in application code on purpose —
examples live in the test-suite and below.

A minimal, Wagtail-managed example (register as a snippet):

.. code-block:: python

   from django.db import models
   from wagtail.snippets.models import register_snippet
   from wagtail.admin.panels import FieldPanel

   from neuromancers_network.notifications.models import EventSubscriber

   @register_snippet
   class BookingApprovedEmail(EventSubscriber):
       subject = models.CharField(max_length=255, blank=True)
       body = models.TextField(blank=True)

       panels = [
           FieldPanel("label"),
           FieldPanel("is_active"),
           FieldPanel("subject"),
           FieldPanel("body"),
       ]

       def handle_event(self, log_entry):
           # ``log_entry.payload`` is the normalized context (recipient ids,
           # meeting title, ...). Render template placeholders and dispatch on a
           # future channel here. Today this is intentionally a no-op besides
           # the base class's log line.
           super().handle_event(log_entry)

Every ``BookingApprovedEmail`` the admin creates in Wagtail is an instance of
this model: create one, set its ``event_type`` to ``booking_approved`` and tick
``is_active``, and the bus will call ``handle_event`` whenever a booking is
approved. Untick ``is_active`` (or delete the instance) to stop receiving.

Scheduled (time-based) events
---------------------------------------------------------------------

Two Celery beat tasks emit time-based events and are idempotent (they never
write a second log row for the same object):

* ``neuromancers_network.notifications.tasks.emit_payment_reminders`` —
  emits ``payment_reminder_due`` for stale ``pending_payment`` bookings.
* ``neuromancers_network.notifications.tasks.emit_upcoming_meetings`` —
  emits ``meeting_upcoming`` for published meetings that start soon and have
  bookings.

They are registered as periodic tasks by the
``notifications`` ``0002_periodic_tasks`` data migration.

Where the tests cover this
---------------------------------------------------------------------

See ``neuromancers_network/notifications/tests/``:

* ``test_event_store.py`` — recording rows and validating event types.
* ``test_bus_dispatch.py`` — active/inactive matching, and error isolation.
* ``test_signals.py`` — database events map to the right bus events.
* ``test_tasks.py`` — scheduled emissions and idempotency.
