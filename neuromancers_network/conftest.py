from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from neuromancers_network.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture(autouse=True)
def _detail_page_structure(request):
    """Create the detail-page tree before tests create detail-backed models."""
    if request.node.get_closest_marker("django_db") is None:
        yield
        return
    request.getfixturevalue("db")

    from neuromancers_network.core.detail_page_structure import (  # noqa: PLC0415
        ensure_detail_page_structure,
    )
    from neuromancers_network.core.models import HomePage  # noqa: PLC0415

    home = HomePage.objects.first()
    if home is not None:
        ensure_detail_page_structure(home)
    yield


@pytest.fixture
def user(db) -> AbstractBaseUser:
    return UserFactory.create()
