from neuromancers_network.core.management.commands.seed_account_selfservice import (
    settings_page_body,
)


def _tabs():
    block = settings_page_body()[0]
    assert block["type"] == "tabs"
    return {tab["key"]: tab for tab in block["value"]["tabs"]}


def _actions(tab):
    return {
        item["value"]["action"]: item["value"]["button"]["audience"]["audience"]
        for item in tab["content"]
        if item["type"] in {"action", "action_form"}
    }


def test_seed_assigns_state_audiences():
    tabs = _tabs()

    assert tabs["provider"]["audience"]["audience"] == ["provider_settings"]
    assert _actions(tabs["privacy"])["account.delete_request"] == [
        "can_delete_account",
    ]
    assert _actions(tabs["security"])["data.export_request"] == [
        "can_request_data_export",
    ]
    assert _actions(tabs["provider"])["peer.subscribe"] == ["can_start_plan"]
    assert _actions(tabs["provider"])["peer.subscription_pause"] == [
        "can_pause_plan",
    ]
    assert _actions(tabs["provider"])["peer.subscription_resume"] == [
        "can_resume_plan",
    ]
    assert _actions(tabs["provider"])["peer.subscription_cancel"] == [
        "can_cancel_plan",
    ]
    assert _actions(tabs["provider"])["peer.connect_stripe"] == [
        "can_connect_stripe",
    ]
    assert _actions(tabs["provider"])["peer.open_stripe_dashboard"] == [
        "can_open_stripe_dashboard",
    ]
    assert _actions(tabs["provider"])["peer.stripe_disconnect"] == [
        "can_disconnect_stripe",
    ]


def test_seed_removes_cancel_deletion_action():
    tabs = _tabs()

    assert "account.delete_cancel" not in _actions(tabs["privacy"])
    assert "account.delete_cancel" not in _actions(tabs["security"])
