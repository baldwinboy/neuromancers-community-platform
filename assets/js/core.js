// Remove any Wagtail admin messages on base site
const wagtailMessages = document.querySelectorAll('.wagtailadmin_messages');
wagtailMessages.forEach((el) => el.remove());
