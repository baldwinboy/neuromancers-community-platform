from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from neuromancers_network.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> AbstractBaseUser:
    return UserFactory.create()
