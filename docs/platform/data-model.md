# Data model

## Identity and profiles

- `users.User` — custom user (Allauth), FSM-backed staff state, deactivation,
  username/email cooldowns.
- `users.UserProfile` — member profile: bio, visibility, country/languages,
  access needs, avatar URL.
- `peers.PeerProfile` — provider profile: approval/verification, provider
  agreement, default terms, public-profile preferences
  (`show_review_rating`, `show_rating_count`, `show_sessions_count`,
  `accepts_reviews`, `reviews_require_approval`).
- `peers.PeerApplication` — application lifecycle (`pending`/`approved`/
  `rejected`); approvals create/approve the peer profile.

## Commerce

- `meetings.Meeting` — a provider's meeting. `meeting_type` is `1:1` or `group`;
  `status` is `draft`/`published`/`archived`; pricing is fixed, per-hour,
  sliding-scale or duration tiers (`MeetingPriceTier`/`MeetingPriceOption`).
- `meetings.Booking` — a seeker's purchase of one or more sessions.
- `meetings.MeetingRequest` — one session (or a request to join a group).
  Statuses: `pending_approval`, `pending_payment`, `approved`, `rejected`,
  `paid`, `completed`, `cancelled`. Records `price_paid`, presentment
  `price_paid_currency`, `price_paid_base` and `price_paid_rate`.
- `meetings.RefundRequest` — one per session; `pending`/`approved`/`rejected`/
  `refunded`.

Rooms and attendance live on both `Meeting` and `MeetingRequest`:
`provider`, `provider_room_id`, `meeting_link`, `host_attended`,
`viewer_attended`.

## Reviews

`meetings.Review` is OneToOne with a completed `MeetingRequest`.
`status` is `pending_approval`, `published` or `hidden`; `is_live` is derived
(`status == published`). Peers may approve or hide but never delete.

## Settings (database-backed)

Registered Wagtail settings in `core/models/settings.py`:

`StripeSettings`, `EmailSettings`, `IntegrationSettings`, `LocalizationSettings`,
`ModerationSettings`, `NotificationSettings`, `AccountSettings`,
`ScriptsSetting`, `ConsentSettings`.

Secret fields are `EncryptedCharField`s (see [Configuration](configuration.md)).

## Inbox, moderation and analytics

- `inbox.NotificationEventLog` (durable event store), `Notification`
  (per-recipient, unique on recipient + event ref), `NotificationPreference`,
  `DaisieBridgeSubscriber`.
- `moderation.EmailBan`, `IPBan`, `UserBlock`, `SupportTicket`,
  `AccountDeletionRequest`, `DeletedIdentity`, `DataExportRequest`.
- `analytics.TransactionLedger`, `SubscriptionLedger`, `SessionLedger`,
  `ActivityLedger` (see [Analytics](analytics.md)).

## Invariants worth preserving

- Detail pages are generated from a source; deleting the source deletes the page
  (`on_delete: "page"`). Two-party records are participant-scoped.
- Ledger and notification writers are idempotent (unique keys / upserts).
- Sessions are stored as UTC; reporting periods are UTC calendar months.
- Financial records are anonymised, never deleted, when an account is purged.
