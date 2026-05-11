---
title: Home
hide:
    - navigation
    - toc
---

# What is dj-stripe?

Dj-stripe is an extensible wrapper around the Stripe API that continuously syncs most of the Stripe Data to your local database as pre-implemented Django Models, out of the box! This allows you to use the Django ORM, in your code, to work with the data making it easier and faster!

For example, if you need to interact with a customer subscription, you can use **dj-stripe’s Subscription Model**, in your code, to get the subscription data for that customer as well as the related models’ data too (if need be and **potentially in 1 database query!**) instead of making multiple slower and unreliable consecutive network calls only to parse through 1 or more of Stripe’s JSON like objects!

# Features

-   **Simplified Security**: We make it simple for you to collect sensitive data such as credit card numbers and remain PCI compliant. This means the sensitive data is sent directly to Stripe instead of passing through your server. For more information, see our Integration Security Guide.

-   **Wallets**: We support all Stripe supported wallets including but not limited to Apple Pay and Google Pay.

-   **Payment methods**: Accepting more payment methods helps your business expand its global reach and improve checkout conversion.

-   **SCA-Ready**: The SDK automatically performs native 3D Secure authentication if needed to comply with Strong Customer Authentication regulation in Europe and other countries as mandated by the law.

-   Support for multiple accounts and API keys → **May be done by the time this website is ready**

-   Tested with Stripe API 2020-08-27 (see API versions)

# Tutorials

The dj-stripe community has come up with some great tutorials:

## Videos

_Video tutorials coming soon! If you have created a video tutorial about dj-stripe, please submit a pull request to add it here._

## Blogs

-   [How to Create a Subscription SaaS Application with Django and Stripe - Sep 2021 - Django 3.2 - dj-stripe 2.4.3](https://www.saaspegasus.com/guides/django-stripe-integrate/)
-   [Using Django and Stripe for Monthly Subscriptions - May 4, 2021 Uses Stripe Elements](https://ordinarycoders.com/blog/article/django-stripe-monthly-subscription)
-   [Django Stripe Integration with using dj-stripe - Jun 12, 2020](https://kartaca.com/en/django-stripe-integration-using-dj-stripe/)

**Have a blog, video or online publication? Write about your dj-stripe tips and tricks, then send us a pull request with the link.**

---

## Installation

### Get the distribution

Install dj-stripe with pip:

```bash
pip install dj-stripe
```

Or with [Poetry](https://python-poetry.org/) (recommended):

```bash
poetry add dj-stripe
```

### Configuration

Add `djstripe` to your `INSTALLED_APPS`:

```bash
INSTALLED_APPS =(
    ...
    "djstripe",
    ...
)
```

Add to urls.py:

```bash
path("stripe/", include("djstripe.urls", namespace="djstripe")),
```

Tell Stripe about the webhook (Stripe webhook docs can be found
[here](https://stripe.com/docs/webhooks)) using the full URL of your
endpoint from the urls.py step above (e.g.
`https://example.com/stripe/webhook`).

Add your Stripe keys and set the operating mode:

```bash
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "{your secret key}")
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "{your secret key}")
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
```

_NOTE_: jstripe expects `STRIPE_LIVE_MODE` to be a Boolean Type. In case you use `Bash env vars or equivalent` to inject its value, make sure to convert it to a Boolean type. We highly recommended the library [django-environ](https://django-environ.readthedocs.io/en/latest/)

Sync data from Stripe:

_NOTE_: djstripe expects `APIKeys` of all Stripe Accounts you'd like to sync data for to already be in the DB. They can be Added from Django Admin.

Run the commands:

```bash
python manage.py migrate
python manage.py djstripe_sync_models
```

See [here](stripe_elements_js.md#integrating_stripe_elements-js_sdk) for notes about usage of the Stripe Elements
frontend JS library.

### Running Tests

Assuming the tests are run against PostgreSQL:

```bash
createdb djstripe
pip install tox
tox
```

---

# Managing Stripe API keys

Stripe API keys are stored in the database, and editable from the Django admin.

_NOTE_: By default, keys are visible by anyone who has access to the dj-stripe administration.

## Adding new API keys

You may add new API keys via the Dj-Stripe "API key" administration. The only required
value is the key's "secret" value itself. Example:

![Adding an API key from the Django administration](https://user-images.githubusercontent.com/235410/99198962-2a1f2e00-279c-11eb-96cc-96dee0ba03ac.png)

Once saved, Dj-Stripe will automatically detect whether the key is a public, restricted
or secret key, and whether it's for live or test mode. If it's a secret key, the
matching Account object will automatically be fetched as well and the key will be
associated with it, so that it can be used to communicate with the Stripe API when
dealing with objects belonging to that Account.

## Updating the API keys

When expiring or rolling new secret keys, you should create the new API key in Stripe,
then add it from the Django administration. Whenever you are ready, you may delete the
old key. (It is safe to keep it around, as long as it hasn't expired. Keeping expired
keys in the database may result in errors during usage).

## FAQ

### Why store them in the database?

As we work on supporting multiple Stripe accounts per instance, it is vital for
dj-stripe to have a mechanism to store more than one Stripe API key. It also became
obvious that we may want proper programmatic access to create and delete keys.
Furthermore, API keys are a legitimate upstream Stripe object, and it is not unlikely
the API may allow access to listing other API keys in the future, in which case we will
want to move them to the database anyway.

### Isn't that insecure?

Please do keep your billing database encrypted. There's a copy of all your customers'
billing data on it!

You may also instead create a read-only restricted key with all-read permissions for
dj-stripe. There is no added risk there, given that dj-stripe holds a copy of all your
data regardless.

### I'm using environment variables. Do I need to change anything?

Not at this time. The settings `STRIPE_LIVE_SECRET_KEY` and `STRIPE_TEST_SECRET_KEY` can
still be used.

### What about public keys?

Setting `STRIPE_LIVE_PUBLIC_KEY` and `STRIPE_TEST_PUBLIC_KEY` will be deprecated in
2.5.0. You do not risk anything by leaving them in your settings: They are not used by
Dj-Stripe outside of the Dj-Stripe mixins, which are now themselves deprecated. So you
can safely leave them in your settings, or you can move them to the database as well
(Keys beginning in `pk_test_` and `pk_live_` will be detected as publishable keys).

---

# Upgrading dj-stripe Smooth and Carefully

## Background

In this article, we will share how to upgrade the `dj-stripe` package flawlessly and carefully.

Please keep in mind that `dj-stripe` always squashes the migration files.
Which means its migration files are completely changed, and leading to migration issues.
**So, you can't immediately upgrade your package too far, for example, from `2.4.0` to `2.7.0` because it will cause breaking changes, especially in your database migrations.**

## How to do it?

For example, if your `dj-stripe` version is `2.4.0` and your migration files are referring to the old version.

![old migration file](https://github.com/agusmakmun/agusmakmun.github.io/assets/7134451/d433d048-d3cf-4385-a7f6-f1890acfe206)

First, you need to find which version has that old migration. For example:

1. Search for the latest version that is closest to your package version, for example: `2.4.0` to `2.5.0`.
2. Visit [the releases page link](https://github.com/dj-stripe/dj-stripe/releases) to find it
3. Cross-check the release notes.
4. Find which dj-stripe version is still compatible with your migration file, for example: `0006_2_3.py`.
5. Find the last migration file of the latest version at [/djstripe/migrations/](https://github.com/dj-stripe/dj-stripe/tree/2.5.0/djstripe/migrations) (for example: `0008_2_5.py`) (both files must exist; if not, it means the new version is no longer compatible with your version).
6. Update your requirements file from `dj-stripe==2.4.0` to `dj-stripe==2.5.0`
7. Run the `manage.py migrate djstripe` command _(this command must not fail; if it does, cross-check steps 1-6)._

```bash
$ docker-compose -f local.yml run django python manage.py migrate djstripe
[+] Creating 3/0
 ✔ Container my-project-redis-1     Running
 ✔ Container my-project-mailhog-1   Running
 ✔ Container my-project-postgres-1  Running
PostgreSQL is available
System check identified some issues:

Operations to perform:
  Apply all migrations: djstripe
Running migrations:
  Applying djstripe.0008_2_5... OK
```

8. And then, after migrating it, change your migration file to refer to the new version (e.g., from `0006_2_3` to `0008_2_5`).

![change migration file](https://github.com/agusmakmun/agusmakmun.github.io/assets/7134451/70ebe2d4-d780-4994-b05b-e361fc95dd3d)

9. Repeat the same process for higher version.

If you have an issue with the Stripe version, we can also try upgrading it in your requirements file.
Check out [issue #1842](https://github.com/dj-stripe/dj-stripe/issues/1842#issuecomment-1319185657) for more information.

## Conclusion

1. Find the closest version that compatible with your version _(for doing migration)_.
2. Update the dependency in `requirements.txt` file and then deploy it.
    - Don't forget to run the `python manage.py migrate djstripe` command.
3. Change your migration file to refer to the new version (e.g., from `0006_2_3` to `0008_2_5`), and then deploy it.

## Alternatives

-   [https://stackoverflow.com/a/31122841](https://stackoverflow.com/a/31122841)

--- 

# Create a Stripe Checkout Session

Stripe Checkout is a prebuilt, hosted payment page optimized for conversion. It creates a secure, Stripe-hosted payment page that lets you collect payments quickly.

## Basic Implementation

For your convenience, dj-stripe has provided an example implementation on how to use [`Checkouts`]:

```python
import json
import logging

import stripe
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import DetailView, FormView
from django.views.generic.base import TemplateView

from djstripe import models
from djstripe import settings as djstripe_settings

from . import forms

logger = logging.getLogger(__name__)


User = get_user_model()
stripe.api_key = djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY


class CreateCheckoutSessionView(LoginRequiredMixin, TemplateView):
    """
    Example View to demonstrate how to use dj-stripe to:

     * Create a Stripe Checkout Session (for a new and a returning customer)
     * Add SUBSCRIBER_CUSTOMER_KEY to metadata to populate customer.subscriber model field
     * Fill out Payment Form and Complete Payment

    Redirects the User to Stripe Checkout Session.
    This does a logged in purchase for a new and a returning customer using Stripe Checkout
    """

    template_name = "checkout.html"

    def get_context_data(self, **kwargs):
        """
        Creates and returns a Stripe Checkout Session
        """
        # Get Parent Context
        context = super().get_context_data(**kwargs)

        # to initialise Stripe.js on the front end
        context["STRIPE_PUBLIC_KEY"] = (
            djstripe_settings.djstripe_settings.STRIPE_PUBLIC_KEY
        )

        success_url = self.request.build_absolute_uri(
            reverse("djstripe_example:success")
        )
        cancel_url = self.request.build_absolute_uri(reverse("home"))

        # get the id of the Model instance of djstripe_settings.djstripe_settings.get_subscriber_model()
        # here we have assumed it is the Django User model. It could be a Team, Company model too.
        # note that it needs to have an email field.
        id = self.request.user.id

        # example of how to insert the SUBSCRIBER_CUSTOMER_KEY: id in the metadata
        # to add customer.subscriber to the newly created/updated customer.
        metadata = {
            str(djstripe_settings.djstripe_settings.SUBSCRIBER_CUSTOMER_KEY): id
        }

        try:
            # retreive the Stripe Customer.
            customer = models.Customer.objects.get(subscriber=self.request.user)

            print("Customer Object in DB.")

            # ! Note that Stripe will always create a new Customer Object if customer id not provided
            # ! even if customer_email is provided!
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer=customer.id,
                # payment_method_types=["bacs_debit"],  # for bacs_debit
                payment_intent_data={
                    "setup_future_usage": "off_session",
                    # so that the metadata gets copied to the associated Payment Intent and Charge Objects
                    "metadata": metadata,
                },
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            # "currency": "gbp",  # for bacs_debit
                            "unit_amount": 2000,
                            "product_data": {
                                "name": "Sample Product Name",
                                "images": ["https://i.imgur.com/EHyR2nP.png"],
                                "description": "Sample Description",
                            },
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )

        except models.Customer.DoesNotExist:
            print("Customer Object not in DB.")

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                # payment_method_types=["bacs_debit"],  # for bacs_debit
                payment_intent_data={
                    "setup_future_usage": "off_session",
                    # so that the metadata gets copied to the associated Payment Intent and Charge Objects
                    "metadata": metadata,
                },
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            # "currency": "gbp",  # for bacs_debit
                            "unit_amount": 2000,
                            "product_data": {
                                "name": "Sample Product Name",
                                "images": ["https://i.imgur.com/EHyR2nP.png"],
                                "description": "Sample Description",
                            },
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )

        context["CHECKOUT_SESSION_ID"] = session.id

        return context


class CheckoutSessionSuccessView(TemplateView):
    """
    Template View for showing Checkout Payment Success
    """

    template_name = "checkout_success.html"


class PurchaseSubscriptionView(FormView):
    """
    Example view to demonstrate how to use dj-stripe to:

    * create a Customer
    * add a card to the Customer
    * create a Subscription using that card

    This does a non-logged in purchase for the user of the provided email
    """

    template_name = "purchase_subscription.html"

    form_class = forms.PurchaseSubscriptionForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if models.Plan.objects.count() == 0:
            raise Exception(
                "No Product Plans in the dj-stripe database - create some in your "
                "stripe account and then "
                "run `./manage.py djstripe_sync_models Plan` "
                "(or use the dj-stripe webhooks)"
            )

        context["STRIPE_PUBLIC_KEY"] = (
            djstripe_settings.djstripe_settings.STRIPE_PUBLIC_KEY
        )

        return context

    def form_valid(self, form):
        stripe_source = form.cleaned_data["stripe_source"]
        email = form.cleaned_data["email"]
        plan = form.cleaned_data["plan"]

        # Guest checkout with the provided email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create(username=email, email=email)

        # Create the stripe Customer, by default subscriber Model is User,
        # this can be overridden with djstripe_settings.djstripe_settings.DJSTRIPE_SUBSCRIBER_MODEL
        customer, created = models.Customer.get_or_create(subscriber=user)

        # Add the source as the customer's default card
        customer.add_payment_method(stripe_source)

        # Using the Stripe API, create a subscription for this customer,
        # using the customer's default payment source
        stripe_subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"plan": plan.id}],
            collection_method="charge_automatically",
            # tax_percent=15,
            api_key=djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY,
        )

        # Sync the Stripe API return data to the database,
        # this way we don't need to wait for a webhook-triggered sync
        subscription = models.Subscription.sync_from_stripe_data(stripe_subscription)

        self.request.subscription = subscription

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "djstripe_example:purchase_subscription_success",
            kwargs={"id": self.request.subscription.id},
        )


class PurchaseSubscriptionSuccessView(DetailView):
    template_name = "purchase_subscription_success.html"

    queryset = models.Subscription.objects.all()
    slug_field = "id"
    slug_url_kwarg = "id"
    context_object_name = "subscription"


def create_payment_intent(request):
    if request.method == "POST":
        intent = None
        data = json.loads(request.body)
        try:
            if "payment_method_id" in data:
                # Create the PaymentIntent
                intent = stripe.PaymentIntent.create(
                    payment_method=data["payment_method_id"],
                    amount=1099,
                    currency="usd",
                    confirmation_method="manual",
                    confirm=True,
                    api_key=djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY,
                )
            elif "payment_intent_id" in data:
                intent = stripe.PaymentIntent.confirm(
                    data["payment_intent_id"],
                    api_key=djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY,
                )
        except stripe.error.CardError as e:
            # Display error on client
            return_data = json.dumps({"error": e.user_message}), 200
            return HttpResponse(
                return_data[0], content_type="application/json", status=return_data[1]
            )

        if (
            intent.status == "requires_action"
            and intent.next_action.type == "use_stripe_sdk"
        ):
            # Tell the client to handle the action
            return_data = (
                json.dumps(
                    {
                        "requires_action": True,
                        "payment_intent_client_secret": intent.client_secret,
                    }
                ),
                200,
            )
        elif intent.status == "succeeded":
            # The payment did not need any additional actions and completed!
            # Handle post-payment fulfillment
            return_data = json.dumps({"success": True}), 200
        else:
            # Invalid status
            return_data = json.dumps({"error": "Invalid PaymentIntent status"}), 500
        return HttpResponse(
            return_data[0], content_type="application/json", status=return_data[1]
        )

    else:
        context = {
            "STRIPE_PUBLIC_KEY": djstripe_settings.djstripe_settings.STRIPE_PUBLIC_KEY
        }
        return TemplateResponse(request, "payment_intent.html", context)
```

## Key Points

### Customer-Subscriber Linking

Please note that in order for dj-stripe to create a link between your `customers` and your `subscribers`, you need to add the `DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY` key to the `metadata` parameter of `Checkout`. This has also been demonstrated in the aforementioned example.

### Example Code Structure

The example implementation shows:

-   How to create a checkout session
-   How to handle success and cancel URLs
-   How to properly set metadata for customer linking
-   How to handle the redirect flow

### Integration Steps

1. Create a view that initializes the Checkout Session
2. Set up success and cancel URLs
3. Add the required metadata for customer linking
4. Handle the webhook events for successful payments
5. Redirect users to the Stripe-hosted checkout page

---

# Subscribing a customer to one or more prices (or plans)

## Recommended Approach

```python
# Recommended Approach to use items dict with Prices
## This will subscribe customer to both price_1 and price_2
price_1 = Price.objects.get(nickname="one_price")
price_2 = Price.objects.get(nickname="two_price")
customer = Customer.objects.first()
customer.subscribe(items=[{"price": price_1}, {"price": price_2}])

## This will subscribe customer to price_1
price_1 = Price.objects.get(nickname="one_price")
customer = Customer.objects.first()
customer.subscribe(items=[{"price": price_1}])
```

## Alternate Approach

```python
## (Alternate Approach) This will subscribe customer to price_1
price_1 = Price.objects.get(nickname="one_price")
customer = Customer.objects.first()
customer.subscribe(price=price_1)
```

However in some cases `subscribe()` might not support all the arguments you need for your implementation.
When this happens you can just call the official `stripe.Customer.subscribe()`.

# Manually syncing data with Stripe

If you're using dj-stripe's webhook handlers then data will be
automatically synced from Stripe to the Django database, but in some
circumstances you may want to manually sync Stripe API data as well.

## Command line

You can sync your database with stripe using the management command
[`djstripe_sync_models`][djstripe.management.commands.djstripe_sync_models], e.g. to populate an empty database from an
existing Stripe account.

```bash
    ./manage.py djstripe_sync_models
```

With no arguments this will sync all supported models for all in database API Keys, or a list of
models to sync can also be provided.

```bash
    ./manage.py djstripe_sync_models Invoice Subscription
```

Note that this may be redundant since we recursively sync related
objects.

A list of models to sync can also be provided along with the API Keys.

```bash
    ./manage.py djstripe_sync_models Invoice Subscription --api-keys sk_test_XXX sk_test_YYY
```

This will sync all the Invoice and Subscription data for the given API Keys. Please note that the API Keys sk_test_YYY and sk_test_XXX need to be in the database.

You can manually reprocess events using the management commands
[`djstripe_process_events`][djstripe.management.commands.djstripe_process_events]. By default this processes all events, but
options can be passed to limit the events processed. Note the Stripe API
documents a limitation where events are only guaranteed to be available
for 30 days.

```bash
    # all events
    ./manage.py djstripe_process_events
    # failed events (events with pending webhooks or where all webhook delivery attempts failed)
    ./manage.py djstripe_process_events --failed
    # filter by event type (all payment_intent events in this example)
    ./manage.py djstripe_process_events --type payment_intent.*
    # specific events by ID
    ./manage.py djstripe_process_events --ids evt_foo evt_bar
    # more output for debugging processing failures
    ./manage.py djstripe_process_events -v 2
```

## In Code

To sync in code, for example if you write to the Stripe API and want to
work with the resulting dj-stripe object without having to wait for the
webhook trigger.

This can be done using the classmethod [`sync_from_stripe_data`][djstripe.models.base.StripeModel.sync_from_stripe_data] that
exists on all dj-stripe model classes.

E.g. creating a product using the Stripe API, and then syncing the API
return data to Django using dj-stripe:

---

# Managing subscriptions and payment sources

## Extending subscriptions

For your convenience, dj-stripe provides a [`Subscription.extend(*delta*)`][djstripe.models.billing.Subscription.extend] method

Subscriptions can be extended by using the `Subscription.extend` method,
which takes a positive `timedelta` as its only property. This method is
useful if you want to offer time-cards, gift-cards, or some other
external way of subscribing users or extending subscriptions, while
keeping the billing handling within Stripe.

_WARNING_: Subscription extensions are achieved by manipulating the `trial_end` of
the subscription instance, which means that Stripe will change the
status to `trialing`.

## How to add payment method to a customer

You can use the [`add_payment_method`][djstripe.models.core.Customer.add_payment_method] method on a customer object to add a payment method token to a customer on Stripe, this will allow you to charge the customer later on that payment method since it will be added as the default payment method.

```python
from djstripe.models import Customer

customer = Customer.objects.first() # Get the first customer in the database as an example
customer.add_payment_method("pm_card_visa") # Add a payment method to the customer as the default payment method
```

If you want to add a payment method to a customer without making it the default payment method, you can use the [`add_payment_method`][djstripe.models.core.Customer.add_payment_method] and pass the parameter `set_default=False`:

```python
from djstripe.models import Customer

customer = Customer.objects.first() # Get the first customer in the database as an example
customer.add_payment_method("pm_card_visa", set_default=False) # Add a payment method to the customer without making it the default payment method
```

**IMPORTANT**: Please keep in mind that due to securities concerns, Stripe will not let you send credit card information through their API, so you will need to use a Stripe token to add a payment method to a customer. You can read more about Stripe tokens [here](https://stripe.com/docs/api/tokens).

---

# Creating individual charges

On the subscriber's customer object, use the [`charge`][djstripe.models.core.Customer.charge] method to generate a
Stripe charge. In this example, we're using the user named `admin` as the
subscriber.

```python
from decimal import Decimal
from django.contrib.auth import get_user_model
from djstripe.models import Customer

user = get_user_model().objects.get(username="admin")
customer, created = Customer.get_or_create(subscriber=user)
customer.charge(Decimal("10.00"), currency="usd")  # Create charge for 10.00 USD
```

# Using Stripe Webhooks

## Setting up a new webhook endpoint in dj-stripe

As of dj-stripe 2.7.0, dj-stripe can create its own webhook endpoints on Stripe from the
Django administration.

Create a new webhook endpoint from the Django administration by going to dj-stripe
→ Webhook endpoints → Add webhook endpoint (or `/admin/djstripe/webhookendpoint/add/`).

From there, you can choose an account to create the endpoint for.
If no account is chosen, the default Stripe API key will be used to create the endpoint.
You can also choose to create the endpoint in test mode or live mode.

You may want to change the base URL of the endpoint. This field will be prefilled with
the current site. If you're running on the local development server, you may see
`http://localhost:8000` or similar in there. Stripe won't let you save webhook endpoints
with such a value, so you will want to change it to a real website URL.

When saved from the admin, the endpoint will be created in Stripe with a dj-stripe
specific UUID which will be part of the URL, making it impossible to guess externally
by brute-force.

## Extra configuration

dj-stripe provides the following settings to tune how your webhooks work:

-   [`DJSTRIPE_WEBHOOK_VALIDATION`][djstripe.settings.DjstripeSettings.WEBHOOK_VALIDATION]
-   [`DJSTRIPE_WEBHOOK_EVENT_CALLBACK`][djstripe.settings.DjstripeSettings.WEBHOOK_EVENT_CALLBACK]

## Handling Stripe Webhooks Using Django Signals in dj-stripe

dj-stripe integrates with Django's signals framework to provide a robust mechanism for handling Stripe webhook events. This approach allows developers to react to Stripe events by executing custom logic linked to signal receivers. This document guides you through setting up and using Django signals with dj-stripe to handle various Stripe webhook events efficiently.

### Configuring Webhook Endpoints

Before you can handle webhook events, ensure you've configured your webhook endpoints correctly in Stripe and dj-stripe. This can typically be done from the Django admin panel under dj-stripe → Webhook endpoints.

### Event Processing Flow

1. **Receiving Events**: When Stripe sends a webhook event, dj-stripe receives the data and creates an `Event` object in your Django database.
2. **Emitting Signals**: After storing the event, dj-stripe emits a Django signal corresponding to the event type (e.g., `charge.succeeded`, `payment_method.attached`).
3. **Database Operations by dj-stripe**: dj-stripe also listens to these signals to perform CRUD operations on corresponding Django models, such as `Charge` or `PaymentMethod`. This ensures that your database stays in sync with the Stripe data.
4. **Handling Events**: You can handle these signals with custom functions linked via the `djstripe_receiver` decorator.

The `Event` model class is the `sender` of every webhook signal, and the saved
`Event` instance is passed as the `event` keyword argument. Receivers run
synchronously inside the same request that delivered the webhook, wrapped in a
single database transaction. If any receiver — including dj-stripe's own
internal sync receivers — raises an exception, the transaction is rolled back,
the `webhook_processing_error` signal fires, and the exception is re-raised so
Stripe sees a non-2xx response and retries. Make your handlers idempotent.

Receiver ordering follows Django's standard signal semantics (connection order)
and is not part of dj-stripe's public contract — do not rely on your handler
running before or after dj-stripe's built-in sync handlers. If you need to read
the synced model from the database, retrieve it by ID inside the handler rather
than assuming it has already been written.

### Implementing Custom Event Handlers

To create custom handlers for Stripe webhook events, follow these steps:

#### 1. Set Up Signal Handlers

First, import the necessary modules and decorators from dj-stripe and define functions to handle the events of interest.

```python
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Event, Charge, PaymentMethod

@djstripe_receiver("charge.succeeded")
def handle_charge_succeeded(sender, **kwargs):
    event: Event = kwargs.get("event")
    charge_id = event.data["object"]["id"]
    charge = Charge.objects.get(id=charge_id)
    print("Charge succeeded!")
    print(f"Sender: {sender}")
    print(f"Event: {event}")
    print(f"Charge: {charge}")

@djstripe_receiver("payment_method.attached")
def handle_payment_method_attached(sender, **kwargs):
    event: Event = kwargs.get("event")
    payment_method_id = event.data["object"]["id"]
    payment_method = PaymentMethod.objects.get(id=payment_method_id)
    print("Payment Method Attached!")
    print(f"Sender: {sender}")
    print(f"Event: {event}")
    print(f"Payment Method: {payment_method}")
```

A single receiver can subscribe to multiple event types by passing a list:

```python
@djstripe_receiver([
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
])
def handle_subscription_change(sender, event, **kwargs):
    ...
```

#### 2. Ensure Proper Loading of Handlers

Ensure that your custom signal handlers are loaded at the appropriate time by including their module in your application's startup sequence. Typically, this can be handled in the `apps.py` of your Django application by overriding the `ready()` method.

```python
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'my_app'

    def ready(self):
        import my_app.signals  # ensure your signals are imported
```

## Webhook lifecycle signals

In addition to the per-event signals described above, dj-stripe emits four
signals during the lifecycle of every inbound webhook. These are useful for
cross-cutting concerns like logging, metrics, or auditing, and fire once per
webhook regardless of event type:

-   `djstripe.signals.webhook_pre_validate(instance, api_key)` — before signature validation.
-   `djstripe.signals.webhook_post_validate(instance, api_key, valid)` — after signature validation, including failed validations.
-   `djstripe.signals.webhook_pre_process(instance, api_key)` — before the event is processed. Not fired if validation failed.
-   `djstripe.signals.webhook_post_process(instance, api_key)` — after a successful processing pass.
-   `djstripe.signals.webhook_processing_error(instance, api_key, exception, data)` — when processing raises.

`instance` is the `WebhookEndpoint` model that received the request.

## Official documentation

Stripe docs for types of Events:
[https://stripe.com/docs/api/events/types](https://stripe.com/docs/api/events/types)

Stripe docs for Webhooks: [https://stripe.com/docs/webhooks](https://stripe.com/docs/webhooks)

Django docs for transactions:
[https://docs.djangoproject.com/en/dev/topics/db/transactions/#performing-actions-after-commit](https://docs.djangoproject.com/en/dev/topics/db/transactions/#performing-actions-after-commit)

---

