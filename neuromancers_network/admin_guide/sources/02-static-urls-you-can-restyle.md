# Static URLs You Can Restyle

This page covers only one topic: which front-end URLs an admin can control the look of through Wagtail.

These are visitor-facing pages. You usually edit them from `/cms/pages/`.

| Visitor URL | What page this is | What you can control |
| --- | --- | --- |
| `/` | Home page | Title, introduction, sections, and page-level design overrides. |
| `/about/` | About page | About content and page-level design overrides. |
| `/contact/` | Contact page | Intro text, form fields, thank-you text, and page-level design overrides. |
| `/profile/<username>/` | User profile page | Profile layout blocks and page-level design overrides. |
| `/admin-guide/` | Admin Guide landing page | Intro text and page-level design overrides. |
| `/admin-guide/<topic>/` | Individual admin guide topic pages | Markdown content for a single help topic and page-level design overrides. |

## Important difference: page design vs site design

- **Site Design** changes the default look of the whole site.
- **Page design** changes only one page.

If you change a page design and later remove that override, the page will go back to the site-wide design.

## Pages that are not regular content pages

Some URLs are special and are styled through **settings** instead of normal page editing:

- Login and signup pages use **AllAuth Settings**, **Content Settings**, and the **Theme Wrapper Page**.
- The navbar uses **Navbar Settings**.
- The footer uses **Footer Settings**.
- The site lock screen uses **Site Lock Settings**.

Use the separate guide page called **Site Settings Panels** for those topics.