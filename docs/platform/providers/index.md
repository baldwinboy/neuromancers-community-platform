# Providers

External integrations are configured in the Wagtail admin (database settings)
and their secrets are encrypted at rest (see [Configuration](../configuration.md)
and the [secrets runbook](../../infra/secrets-runbook.md)).

```{toctree}
---
maxdepth: 1
---
stripe
whereby
daily
getpronto
```

## Meeting providers

`IntegrationSettings.meeting_provider` selects `whereby` or `daily`;
`get_provider()` (`core/meeting_providers/registry.py`) resolves the
implementation. Rooms are created by `Meeting.populate_meeting_link` (group) and
`MeetingRequest.populate_meeting_link` (1:1); the result records `meeting_link`,
`provider_room_id` and `provider` on the session so minutes can be attributed
historically.

Both providers deliver join URLs through `MeetingProvider.join_url`, with a
server-enforced window (`meetings/join.py`, `IntegrationSettings.joining_lead_minutes`):
host and guest links differ, and the endpoint re-checks role and window.

Inbound provider webhooks (`/webhooks/whereby/`, `/webhooks/daily/`) are
signature-verified with HMAC-SHA256 using the encrypted webhook secrets, map
`provider_room_id` to a session, and idempotently record minutes and attendance.
See [Whereby](whereby.md) and [Daily](daily.md) for headers and payloads.
