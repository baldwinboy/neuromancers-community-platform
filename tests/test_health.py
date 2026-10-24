import pytest
from django.test import Client
from django.test import override_settings

pytestmark = pytest.mark.django_db

SHA = "a" * 40
SUCCESS = 200


@override_settings(GIT_COMMIT_SHA=SHA)
def test_health_reports_build_revision() -> None:
    response = Client().get("/api/health")

    assert response.status_code == SUCCESS
    assert response.json() == {"status": "ok", "revision": SHA}
