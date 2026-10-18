from __future__ import annotations

import pytest
from django.conf import settings
from django.test import RequestFactory
from django.utils import translation

from neuromancers_network.core.middleware import LocalizationMiddleware

LOCALIZATION = {
    "enabled": False,
    "default_language": "en",
    "detect_browser_language": True,
    "force_default_language": False,
}


@pytest.fixture
def _localization(monkeypatch):
    monkeypatch.setattr(
        "neuromancers_network.core.middleware.get_localization",
        lambda: LOCALIZATION,
    )
    monkeypatch.setattr(
        "neuromancers_network.core.middleware.available_language_choices",
        lambda: [("en", "English")],
    )
    yield
    translation.deactivate()


@pytest.mark.usefixtures("_localization")
def test_disabled_localization_forces_the_default():
    request = RequestFactory().get(
        "/",
        HTTP_COOKIE=f"{settings.LANGUAGE_COOKIE_NAME}=fr",
    )

    LocalizationMiddleware(lambda _request: None)(request)

    assert request.LANGUAGE_CODE == "en"
    assert translation.get_language() == "en"
