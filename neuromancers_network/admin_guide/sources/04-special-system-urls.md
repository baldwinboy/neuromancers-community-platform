# Special System URLs

This page covers only one topic: system URLs that admins should know about, even when they are not directly edited through normal page editing.

| URL | What it does | Editable in Wagtail? |
| --- | --- | --- |
| `/login/` | Sign-in page | Styled through AllAuth Settings, Content Settings, and the Theme Wrapper Page. |
| `/signup/` | Registration page | Styled through AllAuth Settings, Content Settings, and the Theme Wrapper Page. |
| `/logout/` | Signs a user out | No direct content editing. |
| `/account/password/reset/` | Password reset request page | Styled through AllAuth settings and related templates. |
| `/account/email/` | Email management area | Intended to redirect into the user Settings area. |
| `/account/password/change/` | Password change area | Intended to redirect into the user Settings area. |
| `/social/connections/` | Social account connections | Intended to redirect into the user Settings area. |
| `/2fa/authenticate/` | Multi-factor authentication challenge | System flow, not ordinary content editing. |
| `/site-lock/` | Password gate when the site is private | Controlled by Site Lock Settings. |
| `/cookies/` | Cookie consent management | Managed by the cookie consent app. |
| `/api/` | API base URL | For developers and integrations, not ordinary content management. |
| `/admin/` | Django admin | Mostly for technical administration rather than content editing. |

## What this means in practice

- If the URL is part of **account login, signup, security, or password reset**, you usually change its wording or appearance through **AllAuth Settings**, **Content Settings**, or the **Theme Wrapper Page**.
- If the URL is part of **technical administration**, you usually do not edit it as page content.
- If the URL is part of **site lock**, use **Site Lock Settings** rather than editing a normal page.