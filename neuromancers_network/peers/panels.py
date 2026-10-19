"""Admin panels for peer applications."""

from __future__ import annotations

from wagtail.admin.panels import Panel

from neuromancers_network.peers.submissions import answer_rows


class PeerApplicationAnswersPanel(Panel):
    """Read-only table of the answers submitted with an application."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtailadmin/panels/peer_application_answers.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            application = self.instance
            context["answer_rows"] = answer_rows(application)
            context["submitted_at"] = (
                application.submission_record.submit_time
                if application.submission_record_id
                else None
            )
            return context
