"""The TOS reset bulk action honours the listing filters on select-all."""

from __future__ import annotations

import pytest
from django.test import RequestFactory

from neuromancers_network.peers.wagtail_hooks import ResetTosBulkAction
from neuromancers_network.users.models import UserProfile
from neuromancers_network.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_listing_query_honours_listing_filters():
    accepted = UserFactory(accepted_tos=True)
    pending = UserFactory(accepted_tos=False)
    accepted_profile, _ = UserProfile.objects.get_or_create(user=accepted)
    UserProfile.objects.get_or_create(user=pending)

    request = RequestFactory().get("/", {"id": "all", "user__accepted_tos": "true"})
    action = ResetTosBulkAction(request, UserProfile)

    pks = set(action.get_all_objects_in_listing_query(None))

    assert pks == {accepted_profile.pk}


def test_listing_query_without_filter_selects_all():
    UserProfile.objects.get_or_create(user=UserFactory(accepted_tos=True))
    UserProfile.objects.get_or_create(user=UserFactory(accepted_tos=False))

    request = RequestFactory().get("/", {"id": "all"})
    action = ResetTosBulkAction(request, UserProfile)

    pks = set(action.get_all_objects_in_listing_query(None))

    assert len(pks) == UserProfile.objects.count()
