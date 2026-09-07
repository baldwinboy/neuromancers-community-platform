import factory
from djstripe.enums import SubscriptionStatus
from factory.django import DjangoModelFactory

from neuromancers_network.payments.models.profile import PaymentProfile
from neuromancers_network.peers.models import PeerProfile
from neuromancers_network.peers.models import PeerSubscription
from neuromancers_network.users.models import User


class UserFactory(DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")

    class Meta:
        model = User
        django_get_or_create = ("username",)


class CustomerFactory(DjangoModelFactory):
    id = factory.Sequence(lambda n: f"cus_test{n}")
    livemode = False

    class Meta:
        model = "djstripe.Customer"


class AccountFactory(DjangoModelFactory):
    id = factory.Sequence(lambda n: f"acct_test{n}")
    livemode = False

    class Meta:
        model = "djstripe.Account"


class SubscriptionFactory(DjangoModelFactory):
    id = factory.Sequence(lambda n: f"sub_test{n}")
    livemode = False
    customer = factory.SubFactory(CustomerFactory)
    stripe_data = factory.LazyAttribute(
        lambda o: {"status": o.status},
    )

    class Meta:
        model = "djstripe.Subscription"

    class Params:
        status = SubscriptionStatus.active


class PaymentProfileFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    stripe_customer_id = factory.SubFactory(CustomerFactory)
    stripe_connect_account_id = factory.SubFactory(AccountFactory)
    kyc_completed = False

    class Meta:
        model = PaymentProfile


class PeerProfileFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    is_approved = False

    class Meta:
        model = PeerProfile


class PeerSubscriptionFactory(DjangoModelFactory):
    payment_profile = factory.SubFactory(PaymentProfileFactory)
    subscription = factory.SubFactory(SubscriptionFactory)

    class Meta:
        model = PeerSubscription
