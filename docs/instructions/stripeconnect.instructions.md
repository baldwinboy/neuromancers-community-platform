# Stripe-hosted onboarding

Onboard connected accounts by redirecting them to a Stripe-hosted onboarding flow.

Stripe-hosted onboarding handles the collection of business and identity verification information from connected accounts, requiring minimal effort by the platform. It’s a web form hosted by Stripe that renders dynamically based on the capabilities, country, and business type of each connected account.
![](https://b.stripecdn.com/docs-statics-srv/assets/hosted_onboarding_form.e59ba8300f563e43489953f06127f52c.png)

The hosted onboarding form in the Stripe sample integration, [Furever](https://furever.dev/).

# Accounts v2

> This is a Accounts v2 for when accounts-namespace is v2. View the full page at https://docs.stripe.com/connect/hosted-onboarding?accounts-namespace=v2.

Stripe-hosted onboarding supports [networked onboarding](https://docs.stripe.com/connect/networked-onboarding.md), which allows owners of multiple Stripe accounts to share business information between them. When they onboard an account, they can reuse that information from an existing account instead of resubmitting it.

## Customise the onboarding form [Dashboard]

Go to the [Connect settings page](https://dashboard.stripe.com/account/applications/settings) in the Dashboard to customize the visual appearance of the form with your brand’s name, colour and icon. Stripe-hosted onboarding requires this information. Stripe also recommends [collecting bank account information](https://dashboard.stripe.com/settings/connect/payouts/external_accounts) from your connected accounts as they’re onboarding.

## Create an account and pre-fill information [Server-side]

For each connected account, use the Accounts v2 API to [create an Account object](https://docs.stripe.com/api/v2/core/accounts/create.md) with the `merchant` configuration. If you want to charge your connected accounts using subscriptions, also assign the `customer` configuration. To assign a configuration, simply include it in a create or update call. You don’t have to request any of its capabilities.

If you specify the account’s country or request any capabilities for it, then the account owner can’t change its country. Otherwise, it depends on the account’s Dashboard access:

- **Full Stripe Dashboard:** During onboarding, the account owner can select any acquiring country, the same as when signing up for a normal Stripe account. Stripe automatically requests a set of capabilities for the account based on the selected country.
- **Express Dashboard:** During onboarding, the account owner can select from a list of countries that you configure in your platform Dashboard [Onboarding options](https://dashboard.stripe.com/settings/connect/onboarding-options/countries). You can also configure those options to specify the default capabilities to request for accounts in each country.
- **No Stripe Dashboard**: If Stripe is responsible for collecting requirements, then the onboarding flow lets the account owner select any acquiring country. Otherwise, your custom onboarding flow must set the country and request capabilities.

> #### Use include to populate objects in the response
> 
> When you create, retrieve or update an `Account` in API v2, certain properties are only populated in the response if you specify them [in the include parameter](https://docs.stripe.com/api-includable-response-values.md). For any of those properties that you don’t specify, the response includes them as null, regardless of their actual value.

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

account = client.v2.core.accounts.create({
  "contact_email": "furever_contact@example.com",
  "display_name": "Furever",
  "dashboard": "full",
  "identity": {
    "business_details": {"registered_name": "Furever"},
    "country": "us",
    "entity_type": "company",
  },
  "configuration": {
    "customer": {},
    "merchant": {"capabilities": {"card_payments": {"requested": True}}},
  },
  "defaults": {
    "currency": "usd",
    "responsibilities": {"fees_collector": "stripe", "losses_collector": "stripe"},
    "locales": ["en-US"],
  },
  "include": [
    "configuration.customer",
    "configuration.merchant",
    "identity",
    "requirements",
  ],
})
```

The response includes the ID, which you use to reference the `Account` throughout your integration.

### Request capabilities

You can request [capabilities](https://docs.stripe.com/connect/account-capabilities.md#creating) when creating an account by setting the desired capabilities’ `requested` property to true. For accounts with access to the Express Dashboard, you can also configure your [Onboarding options](https://dashboard.stripe.com/settings/connect/onboarding-options/countries) to automatically request certain capabilities when creating an account.

Stripe’s onboarding UIs automatically collect the requirements for requested capabilities. To reduce onboarding effort, request only the capabilities you need.

### Pre-fill information

If you have information about the account holder (such as their name, address, or other details), you can simplify onboarding by providing it when you create or update the account. The onboarding interface asks the account holder to confirm the pre-filled information before accepting the [Connect service agreement](https://docs.stripe.com/connect/service-agreement-types.md). The account holder can edit any pre-filled information before they accept the service agreement, even if you provided the information using the Accounts API.

If you onboard an account and your platform provides it with a URL, prefill the account’s [defaults.profile.business_url](https://docs.stripe.com/api/v2/core/accounts/object.md#v2_account_object-defaults-profile-business_url). If the business doesn’t have a URL, you can prefill its [defaults.profile.product_description](https://docs.stripe.com/api/v2/core/accounts/create.md#v2_create_accounts-defaults-profile-product_description) instead.

When testing your integration, use [test data](https://docs.stripe.com/connect/testing.md) to simulate different outcomes including identity verification, business information verification, payout failures, and more.

## Determine the information to collect

As the platform, you must decide if you want to collect the required information from your connected accounts *up front* (Upfront onboarding is a type of onboarding where you collect all required verification information from your users at sign-up) or *incrementally* (Incremental onboarding is a type of onboarding where you gradually collect required verification information from your users. You collect a minimum amount of information at sign-up, and you collect more information as the connected account earns more revenue). Up-front onboarding collects the `eventually_due` requirements for the account, while incremental onboarding only collects the `currently_due` requirements.

| Onboarding type | Advantages                                                                                                                                                                                                               |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Up-front**    | - Normally requires only one request for all information
  - Avoids the possibility of payout and processing issues due to missed deadlines
  - Exposes potential risk early when accounts refuse to provide information |
| **Incremental** | - Accounts can onboard quickly because they don’t have to provide as much information                                                                                                                                    |

To determine whether to use up-front or incremental onboarding, review the [requirements](https://docs.stripe.com/connect/required-verification-information.md) for your connected accounts’ locations and capabilities. While Stripe tries to minimise any impact to connected accounts, requirements might change over time.

For connected accounts where you’re responsible for requirement collection, you can customise the behaviour of [future requirements](https://docs.stripe.com/connect/handle-verification-updates.md) using the `collection_options` parameter. To collect the account’s future requirements, set [collection_options.future_requirements](https://docs.stripe.com/api/v2/core/account-links/create.md#create_account_links-collection_options-future_requirements) to `include`.

### Collect additional public details

Stripe collects the required public details for each connected account. You can choose additional fields to collect during onboarding according to your business needs. Any fields you choose that Stripe doesn’t require appear as optional, and connected accounts can choose whether to provide them.

1. In the [Public details](https://dashboard.stripe.com/settings/connect/onboarding-options/public-details) settings in the Dashboard, enable the **Collect public details** toggle.
1. Select the fields to show to connected accounts during onboarding.
1. Click **Save**.

#### Available fields

You can collect the following public details:

| Field                                                                            | Description                                                                                                     |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| [Statement descriptor](https://docs.stripe.com/connect/statement-descriptors.md) | The text that appears on a customer’s credit card or bank statement for payments made to the connected account. |
| Customer support phone number                                                    | A phone number customers can call for support related to the connected account.                                 |
| Customer support address                                                         | A mailing address customers can use to contact the connected account.                                           |
| Customer support email                                                           | An email address customers can use to contact the connected account.                                            |

> #### Requirements vary
> 
> Stripe’s requirements vary by connected account based on their business type, country, and requested capabilities. Enable fields to make sure they always appear during onboarding, whether or not they’re required.

## Create an Account Link [Server-side]

Create an [Account Link](https://docs.stripe.com/api/v2/core/account-links/create.md) using the connected account ID and include a [use_case.account_onboarding.refresh_url](https://docs.stripe.com/connect/hosted-onboarding.md#refresh-url) and a [use_case.account_onboarding.return_url](https://docs.stripe.com/connect/hosted-onboarding.md#return-url). Stripe redirects the connected account to the refresh URL if the Account Link URL has already been visited, has expired or is otherwise invalid. Stripe redirects connected accounts to the return URL when they have completed or left the onboarding flow. Additionally, based on the information you need to collect, pass either `currently_due` or `eventually_due` for `use_case.account_onboarding.collection_options.fields`. This example passes `eventually_due` to use up-front onboarding. For incremental onboarding, set it to `currently_due`.

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

account_link = client.v2.core.account_links.create({
  "account": "{{CONNECTEDACCOUNT_ID}}",
  "use_case": {
    "type": "account_onboarding",
    "account_onboarding": {
      "collection_options": {"fields": "eventually_due"},
      "configurations": ["merchant"],
      "return_url": "https://example.com/return",
      "refresh_url": "https://example.com/refresh",
    },
  },
})
```

### Redirect your connected account to the Account Link URL

Redirect the connected account to the Account Link URL to send them to the onboarding flow. You can only use each temporary Account Link URL once, because it grants access to the account holder’s personal information. Authenticate the account in your application before redirecting them to this URL. [Prefill](https://docs.stripe.com/connect/hosted-onboarding.md#prefill-information) any account information before generating the Account Link because you can’t read or write information for the connected account afterward.

> Don’t email, text, or otherwise send account link URLs outside your platform application. Instead, provide them to the authenticated account holder within your application.

#### iOS

#### Swift

```swift
import UIKit
import SafariServices

let BackendAPIBaseURL: String = "" // Set to the URL of your backend server

class ConnectOnboardViewController: UIViewController {

    // ...

    override func viewDidLoad() {
        super.viewDidLoad()

        let connectWithStripeButton = UIButton(type: .system)
        connectWithStripeButton.setTitle("Connect with Stripe", for: .normal)
        connectWithStripeButton.addTarget(self, action: #selector(didSelectConnectWithStripe), for: .touchUpInside)
        view.addSubview(connectWithStripeButton)

        // ...
    }

    @objc
    func didSelectConnectWithStripe() {
        if let url = URL(string: BackendAPIBaseURL)?.appendingPathComponent("onboard-user") {
          var request = URLRequest(url: url)
          request.httpMethod = "POST"
          let task = URLSession.shared.dataTask(with: request) { (data, response, error) in
              guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data, options: []) as? [String : Any],
                  let accountURLString = json["url"] as? String,
                  let accountURL = URL(string: accountURLString) else {
                      // handle error
              }

              let safariViewController = SFSafariViewController(url: accountURL)
              safariViewController.delegate = self

              DispatchQueue.main.async {
                  self.present(safariViewController, animated: true, completion: nil)
              }
          }
        }
    }

    // ...
}

extension ConnectOnboardViewController: SFSafariViewControllerDelegate {
    func safariViewControllerDidFinish(_ controller: SFSafariViewController) {
        // the user may have closed the SFSafariViewController instance before a redirect
        // occurred. Sync with your backend to confirm the correct state
    }
}

```

#### Android

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    xmlns:tools="http://schemas.android.com/tools"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    tools:context=".activity.ConnectWithStripeActivity">

    <Button
        android:id="@+id/connect_with_stripe"
        android:text="Connect with Stripe"
        android:layout_height="wrap_content"
        android:layout_width="wrap_content"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent"
        style="?attr/materialButtonOutlinedStyle"
        />

</androidx.constraintlayout.widget.ConstraintLayout>
```

#### Kotlin

```kotlin
class ConnectWithStripeActivity : AppCompatActivity() {

    private val viewBinding: ActivityConnectWithStripeViewBinding by lazy {
        ActivityConnectWithStripeViewBinding.inflate(layoutInflater)
    }
    private val httpClient = OkHttpClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(viewBinding.root)

        viewBinding.connectWithStripe.setOnClickListener {
            val weakActivity = WeakReference<Activity>(this)
            val request = Request.Builder()
                .url(BACKEND_URL + "onboard-user")
                .post("".toRequestBody())
                .build()
            httpClient.newCall(request)
                .enqueue(object: Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        // Request failed
                    }
                    override fun onResponse(call: Call, response: Response) {
                        if (!response.isSuccessful) {
                            // Request failed
                        } else {
                            val responseData = response.body?.string()
                            val responseJson =
                                responseData?.let { JSONObject(it) } ?: JSONObject()
                            val url = responseJson.getString("url")

                            weakActivity.get()?.let {
                                val builder: CustomTabsIntent.Builder = CustomTabsIntent.Builder()
                                val customTabsIntent = builder.build()
                                customTabsIntent.launchUrl(it, Uri.parse(url))
                            }
                        }
                    }
                })
        }
    }

    internal companion object {
        internal const val BACKEND_URL = "https://example-backend-url.com/"
    }
}
```

## Identify and address requirement updates [Server-side]

Set up your integration to [listen for changes](https://docs.stripe.com/connect/handling-api-verification.md#verification-process) to account requirements. You can test handling new requirements (and how they might disable charges and payouts) with the [test trigger cards](https://docs.stripe.com/connect/testing.md#trigger-cards).

Send a connected account back through onboarding when it has any `currently_due` or `eventually_due` requirements. You don’t need to identify the specific requirements, because the onboarding interface knows what information it needs to collect. For example, if a typo is preventing verification of the account owner’s identity, onboarding prompts them to upload an identity document.

Stripe notifies you about any [upcoming requirements updates](https://support.stripe.com/user/questions/onboarding-requirements-updates) that affect your connected accounts. You can proactively collect this information by reviewing your accounts’ requirements that have a [requested_reasons.code](https://docs.stripe.com/api/v2/core/accounts/retrieve.md#v2_retrieve_accounts-response-requirements-entries-requested_reasons-code) of `future_requirements`.

For connected accounts where Stripe is responsible for collecting requirements, stop receiving updates for identity information after creating an [Account Link](https://docs.stripe.com/api/v2/core/account-links.md) or [Account Session](https://docs.stripe.com/api/account_sessions.md).

Accounts store identity information in the `identity` hash.

### Handle verification errors

Listen to the [v2.core.account[requirements].updated](https://docs.stripe.com/api/v2/core/events/event-types.md?api-version=preview) event. If the account contains any requirements with a [minimum_deadline.status](https://docs.stripe.com/api/v2/core/accounts/retrieve.md#v2_retrieve_accounts-response-requirements-entries-minimum_deadline-status) of `currently_due` when the deadline arrives, the corresponding functionality is disabled and those statuses become `past_due`.

Let your accounts remediate their verification requirements by directing them to the Stripe-hosted onboarding form.
 (See full diagram at https://docs.stripe.com/connect/hosted-onboarding)
## Handle the connected account returning to your platform [Server-side]

The Account Link requires a `refresh_url` and `return_url` to handle all cases in which the connected account is redirected back to your platform. It’s important to implement these correctly to provide the best onboarding flow for your connected accounts.

> You can use HTTP for your `refresh_url` and `return_url` while you’re in a testing environment (for example, to test locally), but live mode only accepts HTTPS. You must update any testing URLs to HTTPS URLs before you go live.

### Refresh URL

Your connected account is redirected to the `refresh_url` when:

- The link has expired (a few minutes have passed since the link was created).
- The link was already visited (the connected account refreshed the page or clicked the **back** or **forward** button).
- The link was shared in a third-party application such as a messaging client that attempts to access the URL to preview it. Many clients automatically visit links, which causes an Account Link to expire.

The `refresh_url` should call a method on your server to create a new Account Link with the same parameters and redirect the connected account to the new Account Link URL.

### Return URL

Stripe redirects the connected account back to this URL when they complete the onboarding flow or click **Save for later** at any point in the flow. It doesn’t mean that all information has been collected or that there are no outstanding requirements on the account. It only means the flow was entered and exited properly.

This URL passes no state. After redirecting a connected account to the `return_url`, determine whether the account completed onboarding. [Retrieve the account](https://docs.stripe.com/api/v2/core/accounts/retrieve.md) and check the [requirements](https://docs.stripe.com/api/v2/core/accounts/retrieve.md#v2_retrieve_accounts-response-requirements) hash for outstanding requirements. Alternatively, listen to the `v2.core.account[requirements].updated` event sent to your webhook endpoint and cache the state of the account in your application. If onboarding is incomplete, provide prompts in your application to allow them to continue onboarding later.

## Handle connected account-initiated updates [Server-side]

Stripe-hosted onboarding also supports connected account-initiated updates to the information they’ve already provided. Listen to the `v2.core.account[requirements].updated` event sent to your webhook endpoint to be notified when the account completes requirements and updates their information.

When you create an Account Link, you can set the `type` to either `account_onboarding` or `account_update`.

> #### Account Link type restriction
> 
> You can create Account Links of type `account_update` only for connected accounts where your platform is responsible for collecting requirements, including Custom accounts. You can’t create them for accounts that have access to a Stripe-hosted Dashboard. If you use [Connect embedded components](https://docs.stripe.com/connect/get-started-connect-embedded-components.md), you can include components that allow your connected accounts to update their own information. For an account without Stripe-hosted Dashboard access where Stripe is liable for negative balances, you must use embedded components.

### Account Links for account_onboarding

Account Links of this type provide a form for inputting outstanding requirements. Use it when you’re onboarding a new connected account, or when an existing user has new requirements (such as when a connected account had already provided enough information, but you requested a new capability that needs additional info). Send them to this type of Account Link to just collect the new information you need.

### Account Links for account_update

Account Links of this type are enabled for accounts where your platform is responsible for requirement collection. `account_update` links display the attributes that are already populated on the account object and allow the connected account to edit previously provided information. Provide an option in your application (for example, “edit my profile” or “update my verification information”) for connected accounts to make updates themselves.

## Browser support

Stripe-hosted onboarding is only supported in web browsers. You can’t use it in embedded web views inside mobile or desktop applications.


# Accounts v1

> This is a Accounts v1 for when accounts-namespace is v1. View the full page at https://docs.stripe.com/connect/hosted-onboarding?accounts-namespace=v1.

Stripe-hosted onboarding supports [networked onboarding](https://docs.stripe.com/connect/networked-onboarding.md), which allows owners of multiple Stripe accounts to share business information between them. When they onboard an account, they can reuse that information from an existing account instead of resubmitting it.

## Customise the onboarding form [Dashboard]

Go to the [Connect settings page](https://dashboard.stripe.com/account/applications/settings) in the Dashboard to customize the visual appearance of the form with your brand’s name, colour and icon. Stripe-hosted onboarding requires this information. Stripe also recommends [collecting bank account information](https://dashboard.stripe.com/settings/connect/payouts/external_accounts) from your connected accounts as they’re onboarding.

## Create an account and pre-fill information [Server-side]

Create a [connected account](https://docs.stripe.com/api/accounts.md) with the default [controller](https://docs.stripe.com/api/accounts/create.md#create_account-controller) properties. See [design an integration](https://docs.stripe.com/connect/interactive-platform-guide.md) to learn more about controller properties. Alternatively, you can create a connected account by specifying an account [type](https://docs.stripe.com/api/accounts/create.md#create_account-type).

If you specify the account’s country or request any capabilities for it, then the account owner can’t change its country. Otherwise, it depends on the account’s Dashboard access:

- **Full Stripe Dashboard:** During onboarding, the account owner can select any acquiring country, the same as when signing up for a normal Stripe account. Stripe automatically requests a set of capabilities for the account based on the selected country.
- **Express Dashboard:** During onboarding, the account owner can select from a list of countries that you configure in your platform Dashboard [Onboarding options](https://dashboard.stripe.com/settings/connect/onboarding-options/countries). You can also configure those options to specify the default capabilities to request for accounts in each country.
- **No Stripe Dashboard**: If Stripe is responsible for collecting requirements, then the onboarding flow lets the account owner select any acquiring country. Otherwise, your custom onboarding flow must set the country and request capabilities.

#### With controller properties

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

# For SDK versions 12.4.0 or lower, remove '.v1' from the following line.
account = client.v1.accounts.create({
  "controller": {
    "fees": {"payer": "application"},
    "losses": {"payments": "application"},
    "stripe_dashboard": {"type": "express"},
  },
})
```

#### With account type

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

# For SDK versions 12.4.0 or lower, remove '.v1' from the following line.
account = client.v1.accounts.create({"type": "standard"})
```

The response includes the ID, which you use to reference the `Account` throughout your integration.

### Request capabilities

You can request [capabilities](https://docs.stripe.com/connect/account-capabilities.md#creating) when creating an account by setting the desired capabilities’ `requested` property to true. For accounts with access to the Express Dashboard, you can also configure your [Onboarding options](https://dashboard.stripe.com/settings/connect/onboarding-options/countries) to automatically request certain capabilities when creating an account.

Stripe’s onboarding UIs automatically collect the requirements for requested capabilities. To reduce onboarding effort, request only the capabilities you need.

### Pre-fill information

If you have information about the account holder (such as their name, address, or other details), you can simplify onboarding by providing it when you create or update the account. The onboarding interface asks the account holder to confirm the pre-filled information before accepting the [Connect service agreement](https://docs.stripe.com/connect/service-agreement-types.md). The account holder can edit any pre-filled information before they accept the service agreement, even if you provided the information using the Accounts API.

If you onboard an account and your platform provides it with a URL, pre-fill the account’s [business_profile.url](https://docs.stripe.com/api/accounts/create.md#create_account-business_profile-url). If the business doesn’t have a URL, you can pre-fill its [business_profile.product_description](https://docs.stripe.com/api/accounts/create.md#create_account-business_profile-product_description) instead.

When testing your integration, use [test data](https://docs.stripe.com/connect/testing.md) to simulate different outcomes including identity verification, business information verification, payout failures, and more.

## Determine the information to collect

As the platform, you must decide if you want to collect the required information from your connected accounts *up front* (Upfront onboarding is a type of onboarding where you collect all required verification information from your users at sign-up) or *incrementally* (Incremental onboarding is a type of onboarding where you gradually collect required verification information from your users. You collect a minimum amount of information at sign-up, and you collect more information as the connected account earns more revenue). Up-front onboarding collects the `eventually_due` requirements for the account, while incremental onboarding only collects the `currently_due` requirements.

| Onboarding type | Advantages                                                                                                                                                                                                               |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Up-front**    | - Normally requires only one request for all information
  - Avoids the possibility of payout and processing issues due to missed deadlines
  - Exposes potential risk early when accounts refuse to provide information |
| **Incremental** | - Accounts can onboard quickly because they don’t have to provide as much information                                                                                                                                    |

To determine whether to use up-front or incremental onboarding, review the [requirements](https://docs.stripe.com/connect/required-verification-information.md) for your connected accounts’ locations and capabilities. While Stripe tries to minimise any impact to connected accounts, requirements might change over time.

For connected accounts where you’re responsible for requirement collection, you can customise the behaviour of [future requirements](https://docs.stripe.com/connect/handle-verification-updates.md) using the `collection_options` parameter. To collect the account’s future requirements, set [`collection_options.future_requirements`](https://docs.stripe.com/api/account_links/create.md#create_account_link-collection_options-future_requirements) to `include`.

### Collect additional public details

Stripe collects the required public details for each connected account. You can choose additional fields to collect during onboarding according to your business needs. Any fields you choose that Stripe doesn’t require appear as optional, and connected accounts can choose whether to provide them.

1. In the [Public details](https://dashboard.stripe.com/settings/connect/onboarding-options/public-details) settings in the Dashboard, enable the **Collect public details** toggle.
1. Select the fields to show to connected accounts during onboarding.
1. Click **Save**.

#### Available fields

You can collect the following public details:

| Field                                                                            | Description                                                                                                     |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| [Statement descriptor](https://docs.stripe.com/connect/statement-descriptors.md) | The text that appears on a customer’s credit card or bank statement for payments made to the connected account. |
| Customer support phone number                                                    | A phone number customers can call for support related to the connected account.                                 |
| Customer support address                                                         | A mailing address customers can use to contact the connected account.                                           |
| Customer support email                                                           | An email address customers can use to contact the connected account.                                            |

> #### Requirements vary
> 
> Stripe’s requirements vary by connected account based on their business type, country, and requested capabilities. Enable fields to make sure they always appear during onboarding, whether or not they’re required.

## Create an Account Link [Server-side]

Create an [Account Link](https://docs.stripe.com/api/account_links/create.md) using the connected account ID and include a [refresh URL](https://docs.stripe.com/connect/hosted-onboarding.md#refresh-url) and a [return URL](https://docs.stripe.com/connect/hosted-onboarding.md#return-url). Stripe redirects the connected account to the refresh URL if the Account Link URL has already been visited, has expired or is otherwise invalid. Stripe redirects connected accounts to the return URL when they have completed or left the onboarding flow. Additionally, based on the information you need to collect, pass either `currently_due` or `eventually_due` for `collection_options.fields`. This example passes `eventually_due` to use up-front onboarding. For incremental onboarding, set it to `currently_due`.

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

# For SDK versions 12.4.0 or lower, remove '.v1' from the following line.
account_link = client.v1.account_links.create({
  "account": "{{CONNECTEDACCOUNT_ID}}",
  "refresh_url": "https://example.com/refresh",
  "return_url": "https://example.com/return",
  "type": "account_onboarding",
  "collection_options": {"fields": "eventually_due"},
})
```

### Redirect your connected account to the Account Link URL

Redirect the connected account to the Account Link URL to send them to the onboarding flow. You can only use each temporary Account Link URL once, because it grants access to the account holder’s personal information. Authenticate the account in your application before redirecting them to this URL. [Prefill](https://docs.stripe.com/connect/hosted-onboarding.md#prefill-information) any account information before generating the Account Link because you can’t read or write information for the connected account afterward.

> Don’t email, text, or otherwise send account link URLs outside your platform application. Instead, provide them to the authenticated account holder within your application.

#### iOS

#### Swift

```swift
import UIKit
import SafariServices

let BackendAPIBaseURL: String = "" // Set to the URL of your backend server

class ConnectOnboardViewController: UIViewController {

    // ...

    override func viewDidLoad() {
        super.viewDidLoad()

        let connectWithStripeButton = UIButton(type: .system)
        connectWithStripeButton.setTitle("Connect with Stripe", for: .normal)
        connectWithStripeButton.addTarget(self, action: #selector(didSelectConnectWithStripe), for: .touchUpInside)
        view.addSubview(connectWithStripeButton)

        // ...
    }

    @objc
    func didSelectConnectWithStripe() {
        if let url = URL(string: BackendAPIBaseURL)?.appendingPathComponent("onboard-user") {
          var request = URLRequest(url: url)
          request.httpMethod = "POST"
          let task = URLSession.shared.dataTask(with: request) { (data, response, error) in
              guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data, options: []) as? [String : Any],
                  let accountURLString = json["url"] as? String,
                  let accountURL = URL(string: accountURLString) else {
                      // handle error
              }

              let safariViewController = SFSafariViewController(url: accountURL)
              safariViewController.delegate = self

              DispatchQueue.main.async {
                  self.present(safariViewController, animated: true, completion: nil)
              }
          }
        }
    }

    // ...
}

extension ConnectOnboardViewController: SFSafariViewControllerDelegate {
    func safariViewControllerDidFinish(_ controller: SFSafariViewController) {
        // the user may have closed the SFSafariViewController instance before a redirect
        // occurred. Sync with your backend to confirm the correct state
    }
}

```

#### Android

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    xmlns:tools="http://schemas.android.com/tools"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    tools:context=".activity.ConnectWithStripeActivity">

    <Button
        android:id="@+id/connect_with_stripe"
        android:text="Connect with Stripe"
        android:layout_height="wrap_content"
        android:layout_width="wrap_content"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent"
        style="?attr/materialButtonOutlinedStyle"
        />

</androidx.constraintlayout.widget.ConstraintLayout>
```

#### Kotlin

```kotlin
class ConnectWithStripeActivity : AppCompatActivity() {

    private val viewBinding: ActivityConnectWithStripeViewBinding by lazy {
        ActivityConnectWithStripeViewBinding.inflate(layoutInflater)
    }
    private val httpClient = OkHttpClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(viewBinding.root)

        viewBinding.connectWithStripe.setOnClickListener {
            val weakActivity = WeakReference<Activity>(this)
            val request = Request.Builder()
                .url(BACKEND_URL + "onboard-user")
                .post("".toRequestBody())
                .build()
            httpClient.newCall(request)
                .enqueue(object: Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        // Request failed
                    }
                    override fun onResponse(call: Call, response: Response) {
                        if (!response.isSuccessful) {
                            // Request failed
                        } else {
                            val responseData = response.body?.string()
                            val responseJson =
                                responseData?.let { JSONObject(it) } ?: JSONObject()
                            val url = responseJson.getString("url")

                            weakActivity.get()?.let {
                                val builder: CustomTabsIntent.Builder = CustomTabsIntent.Builder()
                                val customTabsIntent = builder.build()
                                customTabsIntent.launchUrl(it, Uri.parse(url))
                            }
                        }
                    }
                })
        }
    }

    internal companion object {
        internal const val BACKEND_URL = "https://example-backend-url.com/"
    }
}
```

## Identify and address requirement updates [Server-side]

Set up your integration to [listen for changes](https://docs.stripe.com/connect/handling-api-verification.md#verification-process) to account requirements. You can test handling new requirements (and how they might disable charges and payouts) with the [test trigger cards](https://docs.stripe.com/connect/testing.md#trigger-cards).

Send a connected account back through onboarding when it has any `currently_due` or `eventually_due` requirements. You don’t need to identify the specific requirements, because the onboarding interface knows what information it needs to collect. For example, if a typo is preventing verification of the account owner’s identity, onboarding prompts them to upload an identity document.

Stripe notifies you about any [upcoming requirements updates](https://support.stripe.com/user/questions/onboarding-requirements-updates) that affect your connected accounts. You can proactively collect this information by reviewing the [future requirements](https://docs.stripe.com/api/accounts/object.md#account_object-future_requirements) for your accounts.

For connected accounts where [controller.requirement_collection](https://docs.stripe.com/api/accounts/object.md#account_object-controller-requirement_collection) is `stripe`, stop receiving updates for identity information after creating an [Account Link](https://docs.stripe.com/api/account_links.md) or [Account Session](https://docs.stripe.com/api/account_sessions.md).

Accounts store identity information in the `company` and `individual` hashes.

### Handle verification errors

Listen to the [account.updated](https://docs.stripe.com/api/events/types.md#event_types-account.updated) event. If the account contains any `currently_due` fields when the `current_deadline` arrives, the corresponding functionality is disabled and those fields are added to `past_due`.

Let your accounts remediate their verification requirements by directing them to the Stripe-hosted onboarding form.
 (See full diagram at https://docs.stripe.com/connect/hosted-onboarding)
## Handle the connected account returning to your platform [Server-side]

The Account Link requires a `refresh_url` and `return_url` to handle all cases in which the connected account is redirected back to your platform. It’s important to implement these correctly to provide the best onboarding flow for your connected accounts.

> You can use HTTP for your `refresh_url` and `return_url` while you’re in a testing environment (for example, to test locally), but live mode only accepts HTTPS. You must update any testing URLs to HTTPS URLs before you go live.

### Refresh URL

Your connected account is redirected to the `refresh_url` when:

- The link has expired (a few minutes have passed since the link was created).
- The link was already visited (the connected account refreshed the page or clicked the **back** or **forward** button).
- The link was shared in a third-party application such as a messaging client that attempts to access the URL to preview it. Many clients automatically visit links, which causes an Account Link to expire.

The `refresh_url` should call a method on your server to create a new Account Link with the same parameters and redirect the connected account to the new Account Link URL.

### Return URL

Stripe redirects the connected account back to this URL when they complete the onboarding flow or click **Save for later** at any point in the flow. It doesn’t mean that all information has been collected or that there are no outstanding requirements on the account. It only means the flow was entered and exited properly.

No state is passed with this URL. After a connected account is redirected to the `return_url`, determine if the account has completed onboarding. [Retrieve the account](https://docs.stripe.com/api/accounts/retrieve.md) and check the [requirements](https://docs.stripe.com/api/accounts/object.md#account_object-requirements) hash for outstanding requirements. Alternatively, listen to the `account.updated` event sent to your webhook endpoint and cache the state of the account in your application. If the account hasn’t completed onboarding, provide prompts in your application to allow them to continue onboarding later.

## Handle connected account-initiated updates [Server-side]

Stripe-hosted onboarding also supports connected account-initiated updates to the information they’ve already provided. Listen to the `account.updated` event sent to your webhook endpoint to be notified when the account completes requirements and updates their information.

When you create an Account Link, you can set the `type` to either `account_onboarding` or `account_update`.

> #### Account Link type restriction
> 
> You can create Account Links of type `account_update` only for connected accounts where your platform is responsible for collecting requirements, including Custom accounts. You can’t create them for accounts that have access to a Stripe-hosted Dashboard. If you use [Connect embedded components](https://docs.stripe.com/connect/get-started-connect-embedded-components.md), you can include components that allow your connected accounts to update their own information. For an account without Stripe-hosted Dashboard access where Stripe is liable for negative balances, you must use embedded components.

### Account Links for account_onboarding

Account Links of this type provide a form for inputting outstanding requirements. Use it when you’re onboarding a new connected account, or when an existing user has new requirements (such as when a connected account had already provided enough information, but you requested a new capability that needs additional info). Send them to this type of Account Link to just collect the new information you need.

### Account Links for account_update

Account Links of this type are enabled for accounts where your platform is responsible for requirement collection. `account_update` links display the attributes that are already populated on the account object and allow the connected account to edit previously provided information. Provide an option in your application (for example, “edit my profile” or “update my verification information”) for connected accounts to make updates themselves.

## Browser support

Stripe-hosted onboarding is only supported in web browsers. You can’t use it in embedded web views inside mobile or desktop applications.

---

I am adding a Stripe Connect integration to my application. Please create a sample integration and add detailed code comments explaining each step. If a value needs to be filled in (like an API key), please mark it with a placeholder comment and provide a helpful error if the value is not present.

The sample integration should onboard users to Connect, create products, and have a simple storefront for customers to make purchases.

For any UI, please use clean, simple HTML with basic styling. If relevant, use the current style of my application.

The latest preview version of the Stripe API is `2026-04-22.dahlia` but this will be used automatically by the SDK.

Use the latest version of the SDK package. You can find the latest version of the SDK package at https://github.com/stripe/stripe-$LANG/releases.

Please set up flows for the following:

## Use a "Stripe Client" for all requests

Here are some common ways to create a Stripe Client:
```js
const stripeClient = new Stripe('sk_***')
```

```ruby
stripeClient = Stripe::StripeClient.new("sk_***")
```

```python
stripeClient = StripeClient("sk_***")
```

```php
$stripeClient = new \Stripe\StripeClient(['api_key' => "sk_***"]);
```

```java
StripeClient stripeClient = new StripeClient("sk_***");
```

```go
stripeClient := stripe.NewClient("sk_***")
```

```dotnet
var stripeClient = new StripeClient("sk_***");
```

use the `stripeClient` for all stripe related requests.

The stripe version does not need to be set since it will be used automatically by the SDK.

## Creating Connected Accounts
Create a connected account where the platform is responsible for pricing and fee collection.

When creating connected accounts, use the V2 API with the following properties:

```js
const account = await stripeClient.v2.core.accounts.create({
  display_name: {From User},
  contact_email: {From User},
  identity: {
    country: 'us',
  },
  dashboard: 'express',
  defaults: {
      responsibilities: {
        fees_collector: 'application',
        losses_collector: 'application',
      },
   },
  configuration: {
    recipient: {
       capabilities: {
        stripe_balance: {
          stripe_transfers: {
            requested: true,
          },
        },
      },
    },
  },
});
```

Only use the above properties when creating accounts. Never pass type at the top level. **Do not use top level type: 'express' or type: 'standard' or type 'custom'.**

If there is a DB already setup, store a mapping from the user object to the account ID.

The full V2 object can be seen at https://docs.stripe.com/api/v2/core/accounts/object?api-version=2025-08-27.preview

## Onboarding Connected Accounts

Onboard the connected accounts using Stripe Account Links.
Please make a UI where the user can click "Onboard to collect payments" and also see the current status of onboarding. You should use the accounts API directly to get the status of the account. For this demo, always get the account status from the API directly (Do not store in a database).

Use the V2 account links API to create an account link:

```js
const accountLink = await stripeClient.v2.core.accountLinks.create({
  account: accountId,
  use_case: {
    type: 'account_onboarding',
    account_onboarding: {
      configurations: ['recipient'],
      refresh_url: 'https://example.com',
      return_url: `https://example.com?accountId=${accountId}`,
    },
  },
});
```

(This is just an example, code could be different depending on programming language.)
```js
const account = await stripeClient.v2.core.accounts.retrieve(stripeAccountId, {
  include: ["configuration.recipient", "requirements"],
});

const readyToReceivePayments = account?.configuration
?.recipient?.capabilities?.stripe_balance?.stripe_transfers?.status === "active"
const requirementsStatus =
      account.requirements?.summary?.minimum_deadline?.status;
const onboardingComplete = requirementsStatus !== "currently_due" && requirementsStatus !== "past_due";
```

## Listen for requirements changes on your connected account

Account requirements can change, often due to changes implemented by financial regulators, card networks, and other financial institutions. To set up webhook notifications of requirement changes, create an event destination to listen for Account v2 update events.

1. In your [Stripe Dashboard](https://dashboard.stripe.com), open the Developers menu by clicking **Developers** in the navigation menu footer, then select **Webhooks**.
1. Click **+ Add destination**.
1. In the Events from section, select **Connected accounts**.
1. Select **Show advanced options**. In the Payload style section, select **Thin**.
1. In the Events field, type "v2" to search for v2 event types. Select **v2.account[requirements].updated** and the **v2.account[configuration.configuration_type].capability_status_updated** type for each configuration type used by your connected accounts.

Configure your application to respond to update events by collecting any updated requirements.

Use the following docs to help you parse 'thin' events. You must use thin events for V2 accounts: https://docs.stripe.com/webhooks.md?snapshot-or-thin=thin

You can start a local listener by using the Stripe CLI: https://docs.stripe.com/cli/listen

```bash
stripe listen --thin-events 'v2.core.account[requirements].updated,v2.core.account[.recipient].capability_status_updated' --forward-thin-to <YOUR_LOCAL_ENDPOINT>
```
### Sample code for parsing 'thin' events

```js
const thinEvent = client.parseThinEvent(req.body, sig, webhookSecret);

// Fetch the event data to understand the failure
const event = await client.v2.core.events.retrieve(thinEvent.id);

// Use event.type to determine which event to handle
```

setup handlers for each event type.

## Create Products
Please set up a sample endpoint and user interface to create Stripe products. This should create products at the platform level using the products API (Do not create on the connected account).

You will need to store (either in metadata or in a database) the mapping from product to connected account id.

```js
stripeClient.products.create({
    name: name,
    description: description,
    default_price_data: {
        unit_amount: priceInCents,
        currency: currency,
    },
});
```

## Display Products

Please create a sample UI (a storefront) that displays all products and allows customers to buy a product. This storefront should display all products and all connected accounts.

## Process Charges

Use a Destination Charge with an application fee to monetize the transaction.

```js
stripeClient.checkout.sessions.create(
  {
    line_items: [
      {
        price_data: <Price Data>
        quantity: <Quantity>,
      },
    ],
    payment_intent_data: {
      application_fee_amount: 123,
      transfer_data: {
        destination: '{{CONNECTED_ACCOUNT_ID}}',
      },
    },
    mode: 'payment',
    success_url: '<Root URL>/success?session_id={CHECKOUT_SESSION_ID}',
  }
)
```

Use hosted checkout for simplicity.

## General Tips
Make sure to use the Stripe Client for all requests.

When in doubt reference the stripe docs.

---

# Accept a payment using destination charges

Use destination charges to accept payments.

Create destination charges when customers transact with your platform for products or services provided by your connected accounts and you immediately transfer funds to your connected accounts. With this charge type:

- You create a charge on your platform’s account.
- You determine whether some or all of those funds are transferred to the connected account.
- You’re the *merchant of record* (The legal entity responsible for facilitating the sale of products to a customer that handles any applicable regulations and liabilities, including sales taxes. In a Connect integration, it can be the platform or a connected account) and your account balance gets debited for the cost of the Stripe fees, refunds and chargebacks.

With [certain exceptions](https://docs.stripe.com/connect/account-capabilities.md#transfers-cross-border), if your platform and a connected account aren’t in the same region, you must specify the connected account as the [settlement merchant](https://docs.stripe.com/connect/destination-charges.md#settlement-merchant) using the [on_behalf_of](https://docs.stripe.com/api/payment_intents/create.md#create_payment_intent-on_behalf_of) parameter on the Payment Intent.

If you use destination charges with `on_behalf_of`, you need to add both the [recipient](https://docs.stripe.com/connect/account-capabilities.md#recipient) and [merchant](https://docs.stripe.com/connect/account-capabilities.md#merchant) configurations when you [set up the connected account](https://docs.stripe.com/connect/marketplace/tasks/create.md). The `recipient` configuration allows the connected account to receive [Transfers](https://docs.stripe.com/api/transfers/object.md?api-version=preview), and the `merchant` configuration enables them to be the *merchant of record* (The legal entity responsible for facilitating the sale of products to a customer that handles any applicable regulations and liabilities, including sales taxes. In a Connect integration, it can be the platform or a connected account).

This guide shows you how to create a Stripe-hosted Checkout Session. Alternatively, you can use [Stripe Elements](https://docs.stripe.com/payments/elements.md) or the [API](https://docs.stripe.com/api/checkout/sessions/create.md).

## Create a Checkout Session [Server-side]

A [Checkout Session](https://docs.stripe.com/api/checkout/sessions.md) controls what your customer sees in the payment form such as line items, the order amount and currency and acceptable payment methods. Add a checkout button to your website that calls a server-side endpoint to create a Checkout Session.

On your server, create a Checkout Session and redirect your customer to the [URL](https://docs.stripe.com/api/checkout/sessions/object.md#checkout_session_object-url) returned in the response.

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

# For SDK versions 12.4.0 or lower, remove '.v1' from the following line.
session = client.v1.checkout.sessions.create({
  "line_items": [
    {
      "price_data": {
        "currency": "usd",
        "product_data": {"name": "T-shirt"},
        "unit_amount": 1000,
      },
      "quantity": 1,
    },
  ],
  "payment_intent_data": {
    "application_fee_amount": 123,
    "transfer_data": {"destination": "{{CONNECTEDACCOUNT_ID}}"},
  },
  "mode": "payment",
  "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
})
```

| Parameter                                                                                                                                                                 | Value                     | Required?            | Description                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [payment_intent_data[transfer_data]](https://docs.stripe.com/api/checkout/sessions/create.md#create_checkout_session-payment_intent_data-transfer_data-destination)       | `destination`             | Yes                  | Indicates that this is a destination charge. A destination charge means the charge is processed on the platform and then the funds are immediately and automatically transferred to the connected account’s pending balance.                                                                                                                                               |
| [line_items](https://docs.stripe.com/api/checkout/sessions/create.md#create_checkout_session-line_items)                                                                  | A list of up to 100 items | Yes                  | The items the customer is purchasing. The items are displayed in the embedded payment form.                                                                                                                                                                                                                                                                                |
| [success_url](https://docs.stripe.com/api/checkout/sessions/create.md#create_checkout_session-success_url)                                                                | A valid URL               | Yes                  | The URL where the customer is redirected after they complete a payment. Use the value of `{CHECKOUT_SESSION_ID}` to retrieve the Checkout Session and inspect its status to decide what to show your customer. You can also append [custom query parameters](https://docs.stripe.com/payments/checkout/custom-success-page.md) which persist through the redirect process. |
| [payment_intent_data[application_fee_amount]](https://docs.stripe.com/api/checkout/sessions/create.md#create_checkout_session-payment_intent_data-application_fee_amount) | An amount of money        | Required for Connect | The amount your platform plans to take from the transaction. The full charge amount is immediately transferred from the platform to the connected account that’s specified by `transfer_data[destination]` after the charge is captured. The `application_fee_amount` is then transferred back to the platform and the Stripe fee is deducted from the platform’s amount.  |
 (See full diagram at https://docs.stripe.com/connect/marketplace/tasks/accept-payment/destination-charges)
## Handle post-payment events for destination charges [Server-side]

Stripe sends a [checkout.session.completed](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.completed) event when the payment completes. [Use a webhook to receive these events](https://docs.stripe.com/webhooks/quickstart.md) and run actions, such as sending an order confirmation email to your customer, logging the sale in a database, or starting a shipping workflow.

Listen for these events rather than waiting on a callback from the client. On the client, the customer could close the browser window or quit the app before the callback executes. Some payment methods also take 2-14 days for payment confirmation. Setting up your integration to listen for asynchronous events enables you to accept multiple [payment methods](https://stripe.com/payments/payment-methods-guide) with a single integration.

Handle the following events when collecting payments with Checkout:

| Event                                                                                                                                        | Description                                                                           | Next steps                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [checkout.session.completed](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.completed)                             | The customer has successfully authorised the payment by submitting the Checkout form. | Wait for the payment to succeed or fail.                                |
| [checkout.session.async_payment_succeeded](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.async_payment_succeeded) | The customer’s payment succeeded.                                                     | Fulfil the purchased goods or services.                                 |
| [checkout.session.async_payment_failed](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.async_payment_failed)       | The payment was declined, or failed for some other reason.                            | Contact the customer via email and request that they place a new order. |

These events all include the [Checkout Session](https://docs.stripe.com/api/checkout/sessions.md) object. After the payment succeeds, the underlying *PaymentIntent* (The Payment Intents API tracks the lifecycle of a customer checkout flow and triggers additional authentication steps when required by regulatory mandates, custom Radar fraud rules, or redirect-based payment methods) [status](https://docs.stripe.com/payments/paymentintents/lifecycle.md) changes from `processing` to `succeeded` or a failure status.

## Next steps

After you can process payments, monetise your marketplace by [collecting application fees](https://docs.stripe.com/connect/marketplace/tasks/app-fees.md) from your connected accounts.

---

# Accept a payment using separate charges and transfers

Use separate charges and transfers to accept payments.

Create separate charges and transfers to transfer funds from one payment to multiple connected accounts or when a specific user isn’t known at the time of the payment. The charge on your platform account is decoupled from the transfers to your connected accounts. With this charge type:

- You create a charge on your platform’s account and also transfer funds to your connected accounts. The payment appears as a charge on your account and there are also transfers to connected accounts (amount determined by you), which are withdrawn from your account balance.
- You can transfer funds to multiple connected accounts.
- You’re the *merchant of record* (The legal entity responsible for facilitating the sale of products to a customer that handles any applicable regulations and liabilities, including sales taxes. In a Connect integration, it can be the platform or a connected account) and your account balance gets debited for the cost of the Stripe fees, refunds and chargebacks.

This charge type helps marketplaces split payments between multiple parties. For example, a restaurant delivery platform that splits payments between the restaurant and the deliverer.

> Funds segregation is a private preview feature that keeps payment funds in a protected holding state before you transfer them to connected accounts. This prevents allocated funds from being used for unrelated platform operations. Contact your Stripe account manager to request access.

## Create a Checkout Session [Server-side]

A [Checkout Session](https://docs.stripe.com/api/checkout/sessions.md) controls what your customer sees in the payment form such as line items, the order amount and currency and acceptable payment methods. Add a checkout button to your website that calls a server-side endpoint to create a Checkout Session.

On your server, create a Checkout Session and redirect your customer to the [URL](https://docs.stripe.com/api/checkout/sessions/object.md#checkout_session_object-url) returned in the response.

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

# For SDK versions 12.4.0 or lower, remove '.v1' from the following line.
session = client.v1.checkout.sessions.create({
  "line_items": [
    {
      "price_data": {
        "currency": "usd",
        "product_data": {"name": "Restaurant delivery service"},
        "unit_amount": 10000,
      },
      "quantity": 1,
    },
  ],
  "payment_intent_data": {"transfer_group": "ORDER100"},
  "mode": "payment",
  "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
})
```

| Parameter                                                                                                                                                 | Value                                                               | Required?              | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [line_items](https://docs.stripe.com/api/checkout/sessions/create.md#create_checkout_session-line_items)                                                  | A list of items the customer is purchasing.                         | Required conditionally | This attribute represents the items the customer is purchasing. The items are displayed in the Stripe-hosted checkout page.                                                                                                                                                                                                                                                                                                                                                                                         |
| [payment_intent_data[transfer_group]](https://docs.stripe.com/api/checkout/sessions/create.md#create_checkout_session-payment_intent_data-transfer_group) | A unique string that identifies a payment as being part of a group. | Yes                    | When Stripe automatically creates a charge for a PaymentIntent with a `transfer_group` value, it assigns the same value to the charge’s `transfer_group`.                                                                                                                                                                                                                                                                                                                                                           |
| [success_url](https://docs.stripe.com/api/checkout/sessions/create.md#create_checkout_session-success_url)                                                | A valid URL                                                         | Yes                    | Stripe redirects the customer to the success URL after they complete a payment and replaces the `{CHECKOUT_SESSION_ID}` string with the Checkout Session ID. Use this to retrieve the Checkout Session and inspect the status to decide what to show your customer. You can also append your own query parameters, which persist through the redirect process. See [customise redirect behaviour with a Stripe-hosted page](https://docs.stripe.com/payments/checkout/custom-success-page.md) for more information. |
 (See full diagram at https://docs.stripe.com/connect/marketplace/tasks/accept-payment/separate-charges-and-transfers)
## Handle post-payment events for separate charges and transfers [Server-side]

Stripe sends a [checkout.session.completed](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.completed) event when the payment completes. [Use a webhook to receive these events](https://docs.stripe.com/webhooks/quickstart.md) and run actions, such as sending an order confirmation email to your customer, logging the sale in a database, or starting a shipping workflow.

Listen for these events instead of waiting on a callback from the client. On the client, the customer could close the browser window or quit the app before the callback executes. Some payment methods also take 2-14 days for payment confirmation. Setting up your integration to listen for asynchronous events enables you to accept multiple [payment methods](https://stripe.com/payments/payment-methods-guide) with a single integration.

Handle the following events when collecting payments with Checkout:

| Event                                                                                                                                        | Description                                                                           | Next steps                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [checkout.session.completed](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.completed)                             | The customer has successfully authorised the payment by submitting the Checkout form. | Wait for the payment to succeed or fail.                                |
| [checkout.session.async_payment_succeeded](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.async_payment_succeeded) | The customer’s payment succeeded.                                                     | Fulfil the purchased goods or services.                                 |
| [checkout.session.async_payment_failed](https://docs.stripe.com/api/events/types.md#event_types-checkout.session.async_payment_failed)       | The payment was declined, or failed for some other reason.                            | Contact the customer via email and request that they place a new order. |

These events all include the [Checkout Session](https://docs.stripe.com/api/checkout/sessions.md) object. After the payment succeeds, the underlying *PaymentIntent* (The Payment Intents API tracks the lifecycle of a customer checkout flow and triggers additional authentication steps when required by regulatory mandates, custom Radar fraud rules, or redirect-based payment methods) [status](https://docs.stripe.com/payments/paymentintents/lifecycle.md) changes from `processing` to `succeeded` or a failure status.

## Create a transfer [Server-side]

On your server, send funds from your account to a connected account by creating a [Transfer](https://docs.stripe.com/api/transfers/create.md) and specifying the `transfer_group` used.

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

# For SDK versions 12.4.0 or lower, remove '.v1' from the following line.
transfer = client.v1.transfers.create({
  "amount": 7000,
  "currency": "usd",
  "destination": "{{CONNECTEDACCOUNT_ID}}",
  "transfer_group": "ORDER100",
})
```

Transfer and charge amounts don’t have to match. You can split a single charge between multiple transfers or include multiple charges in a single transfer. The following example creates an additional transfer associated with the same `transfer_group`.

```python
# Don't put any keys in code. See https://docs.stripe.com/keys-best-practices.
# Find your keys at https://dashboard.stripe.com/apikeys.
client = StripeClient("<<YOUR_SECRET_KEY>>")

# For SDK versions 12.4.0 or lower, remove '.v1' from the following line.
transfer = client.v1.transfers.create({
  "amount": 2000,
  "currency": "usd",
  "destination": "{{OTHER_CONNECTED_ACCOUNT_ID}}",
  "transfer_group": "ORDER100",
})
```

### Transfer options

You can assign any value to the `transfer_group` string, but it must represent a single business action. You can also make a transfer with neither an associated charge nor a `transfer_group` – for example, when you must pay a provider but there’s no associated customer payment.

> The `transfer_group` only identifies associated objects. It doesn’t affect any standard functionality. To prevent a transfer from executing before the funds from the associated charge are available, use the transfer’s `source_transaction` attribute.

By default, a transfer request fails when the amount exceeds the platform’s [available account balance](https://docs.stripe.com/connect/account-balances.md). Stripe doesn’t automatically retry failed transfer requests.

You can avoid failed transfer requests for transfers that are associated with charges. When you specify the associated charge [as the transfer’s source_transaction](https://docs.stripe.com/connect/marketplace/tasks/accept-payment/separate-charges-and-transfers.md#transfer-options), the transfer request automatically succeeds. However, we don’t execute the transfer until the funds from that charge are available in the platform account.

> If you use separate charges and transfers, take that into account when planning your *payout* (A payout is the transfer of funds to an external account, usually a bank account, in the form of a deposit) schedule. Automatic payouts can interfere with transfers that don’t have a defined `source_transaction`.

## Geographic availability

Stripe supports separate charges and transfers in the following regions:

- AT
- AU
- BE
- BG
- BR
- CA
- CH
- CY
- CZ
- DE
- DK
- EE
- ES
- FI
- FR
- GB
- GR
- HR
- HU
- IE
- IT
- JP
- LI
- LT
- LU
- LV
- MT
- MX
- MY
- NL
- NO
- NZ
- PL
- PT
- RO
- SE
- SG
- SI
- SK
- US

Stripe supports cross-border transfers on the payments balance between the United States, Canada, United Kingdom, the EEA and Switzerland. In other scenarios, your platform and any connected account must be in the same region. Attempting to transfer funds across unsupported borders or balances returns an error. See [Cross-border payouts](https://docs.stripe.com/connect/cross-border-payouts.md) for supported funds flows between other regions.

You must only use transfers in combination with the permitted use cases for [charges](https://docs.stripe.com/connect/charges.md), [tops-ups](https://docs.stripe.com/connect/top-ups.md) and [fees](https://docs.stripe.com/connect/marketplace/tasks/accept-payment/separate-charges-and-transfers.md#collect-fees). We recommend using separate charges and transfers only when you’re responsible for negative balances of your connected accounts.

## Next steps

After you can process payments, monetise your marketplace by [collecting application fees](https://docs.stripe.com/connect/marketplace/tasks/app-fees.md) from your connected accounts.