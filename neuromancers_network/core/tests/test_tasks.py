from unittest.mock import patch

import pytest

from neuromancers_network.core.tasks import update_search_index

pytestmark = pytest.mark.django_db


class TestUpdateSearchIndex:
    def test_calls_update_index_command(self):
        with patch("neuromancers_network.core.tasks.call_command") as call_command:
            update_search_index()

        call_command.assert_called_once_with("update_index")
