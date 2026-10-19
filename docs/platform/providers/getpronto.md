# GetPronto

GetPronto handles **file and image uploads**, not video. It stores member avatars
and files attached to admin-authored forms.

- Client: `getpronto/` (clientele-generated). The API key lives in
  `IntegrationSettings.getpronto_api_key` (encrypted).
- Avatar flow (`users/avatar.py`): `presign_upload` → PUT the bytes to the
  presigned URL (20-second timeout) → `confirm_upload`; the previous file is
  deleted on success. Tenant/API wiring is in `core/apis.py`.
- Form file uploads use the same client through handlers configured in
  `WAGTAIL_DAISIE_FORM_FIELD_TYPES` (for example `store_document`).

GetPronto is exposed in the admin under Integration Settings alongside Whereby
and Daily, but it does not create meeting rooms and does not appear in the
meeting-provider selector.
