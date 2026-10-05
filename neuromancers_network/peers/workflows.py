"""daisIE approval-workflow handlers for peer applications."""

from __future__ import annotations


def approve_peer_application(application):
    """Convert an approved peer application into an approved peer profile.

    Runs from ``WAGTAIL_DAISIE_APPROVAL_WORKFLOWS`` when ``is_approved`` flips
    to True. Delegates to :meth:`PeerApplication.approve`, which keeps
    ``status``/``is_approved`` in sync and creates/approves the peer profile.
    """
    if application.status != "approved":
        return None
    return application.approve(reviewer=application.reviewed_by)
