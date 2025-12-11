import random
from datetime import timedelta

import factory
from django.utils import timezone
from guardian.shortcuts import assign_perm

from apps.accounts.models_users.user import UserGroup

from .choices import GroupSessionOccurrenceChoices, SessionAvailabilityOccurrenceChoices
from .models import (
    FilterSettings,
    GroupSession,
    GroupSessionDetailPage,
    PeerSession,
    PeerSessionAvailability,
    PeerSessionDetailPage,
    SessionsIndexPage,
)
from .utils import get_host_user, stable_durations, stable_langs, stable_price


class PeerSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PeerSession

    host = factory.LazyFunction(get_host_user)

    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("paragraph")
    languages = factory.LazyFunction(stable_langs)
    durations = factory.LazyFunction(stable_durations)
    currency = "GBP"

    price = factory.LazyFunction(stable_price)
    concessionary_price = factory.LazyFunction(lambda: random.choice([None, 500]))

    per_hour_price = factory.LazyFunction(lambda: random.choice([None, 2000, 3000]))
    concessionary_per_hour_price = factory.LazyFunction(
        lambda: random.choice([None, 1000])
    )

    is_published = factory.Faker("boolean", chance_of_getting_true=60)

    @factory.lazy_attribute
    def filters(self):
        # Randomly select some groups
        selected = {}
        normalized = FilterSettings.objects.first().as_normalized_mapping()

        for group_slug, group in normalized.items():
            # randomly include this group or skip it
            if random.choice([True, False]):
                items = {
                    k: v
                    for k, v in group["items"].items()
                    if random.choice([True, False])
                }
                if items:
                    selected[group_slug] = {
                        "slug": group["slug"],
                        "label": group["label"],
                        "items": items,
                    }
        return selected

    @factory.post_generation
    def add_permissions(self, create, extracted, **kwargs):
        if not create:
            return

        # Ensure host gets extra perms when a session is created
        perms = ["manage_availability", "schedule_session"]
        for codename in perms:
            assign_perm(codename, self.host, self)

        if self.is_published:
            group = UserGroup.objects.get(name="Support Seeker")
            assign_perm("request_session", group, self)

    @factory.post_generation
    def add_wagtail_page(self, create, extracted, **kwargs):
        if not create:
            return

        parent_page = SessionsIndexPage.objects.first()
        if not parent_page:
            raise Exception("No SessionsIndexPage exists to add the event page under.")
        session_page = PeerSessionDetailPage(
            title=self.title,
            slug=f"peer-{self.pk}",
            session=self,
        )
        parent_page.add_child(instance=session_page)
        session_page.save_revision().publish()
        session_page.set_url_path(parent_page)


class PeerSessionAvailabilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PeerSessionAvailability

    session = factory.SubFactory(PeerSessionFactory)

    starts_at = factory.Faker(
        "date_time_between_dates",
        datetime_start=timezone.now(),
        datetime_end=timezone.now() + timedelta(days=random.randint(1, 10)),
    )

    ends_at = factory.LazyAttribute(
        lambda o: o.starts_at + timedelta(minutes=random.randint(5, 24 * 60))
    )

    occurrence = factory.Iterator(
        [choice[0] for choice in SessionAvailabilityOccurrenceChoices.choices] + [None]
    )

    @factory.lazy_attribute
    def occurrence_starts_at(self):
        if not self.occurrence:
            return None

        if random.random() > 0.3:
            return self.ends_at + timedelta(minutes=random.randint(5, 24 * 60))

        return None

    @factory.lazy_attribute
    def occurrence_ends_at(self):
        if not self.occurrence or not self.occurrence_starts_at:
            return None

        if random.random() > 0.3:
            return self.occurrence_starts_at + timedelta(days=random.randint(1, 365))

        return None


class GroupSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupSession

    host = factory.LazyFunction(get_host_user)

    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("paragraph")
    language = factory.LazyFunction(lambda: random.choice(["en", "fr", "es"]))

    starts_at = factory.Faker(
        "date_time_between_dates",
        datetime_start=timezone.now(),
        datetime_end=timezone.now() + timedelta(days=random.randint(1, 10)),
    )

    ends_at = factory.LazyAttribute(
        lambda o: o.starts_at + timedelta(minutes=random.randint(5, 120))
    )

    currency = "GBP"
    price = factory.LazyFunction(lambda: random.choice([0, 500, 1000]))
    concessionary_price = factory.LazyFunction(lambda: random.choice([None, 500]))
    access_before_payment = True
    is_published = factory.Faker("boolean", chance_of_getting_true=60)
    capacity = factory.LazyFunction(lambda: random.randint(1, 20))
    meeting_link = None  # can be set later or generated dynamically

    recurring = factory.Faker("boolean", chance_of_getting_true=60)

    @factory.lazy_attribute
    def filters(self):
        # Randomly select some groups
        selected = {}
        normalized = FilterSettings.objects.first().as_normalized_mapping()

        for group_slug, group in normalized.items():
            # randomly include this group or skip it
            if random.choice([True, False]):
                items = {
                    k: v
                    for k, v in group["items"].items()
                    if random.choice([True, False])
                }
                if items:
                    selected[group_slug] = {
                        "slug": group["slug"],
                        "label": group["label"],
                        "items": items,
                    }
        return selected

    @factory.lazy_attribute
    def recurrence_type(self):
        if not self.recurring:
            return None

        return random.choice(
            [choice[0] for choice in GroupSessionOccurrenceChoices.choices]
        )

    @factory.lazy_attribute
    def recurrence_ends_at(self):
        if not self.recurring:
            return None

        if random.random() > 0.3:
            return self.ends_at + timedelta(days=random.randint(1, 365))

        return None

    @factory.post_generation
    def add_permissions(self, create, extracted, **kwargs):
        if not create or not self.is_published:
            return

        # Assign request join session permission to Support Seeker group
        group = UserGroup.objects.get(name="Support Seeker")
        assign_perm("request_join_session", group, self)

    @factory.post_generation
    def add_wagtail_page(self, create, extracted, **kwargs):
        if not create:
            return

        parent_page = SessionsIndexPage.objects.first()
        if not parent_page:
            raise Exception("No SessionsIndexPage exists to add the event page under.")
        session_page = GroupSessionDetailPage(
            title=self.title,
            slug=f"group-{self.pk}",
            session=self,
        )
        parent_page.add_child(instance=session_page)
        session_page.save_revision().publish()
        session_page.set_url_path(parent_page)
