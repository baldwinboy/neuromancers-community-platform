# Site Settings Panels

This page covers only one topic: the panels under `/cms/settings/` and what each one controls.

| Settings panel | What it controls |
| --- | --- |
| Site Design | Site-wide colours, typography, backgrounds, and default logo. |
| Email Settings | SMTP host, port, username, password, encryption, and default sender address. |
| Site Lock Settings | Whether the site is public, whether a password is required, and the maintenance message shown to visitors. |
| Content Settings | Terminology such as Host, Attendee, Session, plus AllAuth form labels and help text. |
| External API Settings | GetPronto, MJML, Stripe, and Whereby keys and related options. |
| Navbar Settings | Navbar background, design, position, logo, and custom CSS. |
| Footer Settings | Footer background, columns, newsletter area, social icons, and copyright text. |
| AllAuth Settings | Light and dark designs for login, signup, and related account pages. |

## Most common tasks and where they live

- **Change the site logo**: Site Design or Navbar Settings.
- **Change login page wording**: Content Settings.
- **Change login page colours**: AllAuth Settings.
- **Change the footer links**: Footer Settings.
- **Add Stripe keys**: External API Settings.
- **Hide the site behind a password**: Site Lock Settings.

## A simple rule of thumb

If the same change should appear on many pages, try `/cms/settings/` first.

If the change should affect only one page, edit that page in `/cms/pages/` instead.