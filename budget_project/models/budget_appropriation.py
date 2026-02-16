import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    def action_post(self):
        super().action_post()
        self._log_message_on_linked_documents()

    def _log_message_on_linked_documents(self):
        project_lines = self.line_ids.filtered(lambda l: l.budget_project_id)
        if not project_lines:
            return

        # Post a single consolidated message on budget.appropriation
        body_parts = []
        for line in project_lines:
            body_parts.append(line._message_link_to_budget_project())

        if body_parts:
            self.message_post(
                body="<br/>".join(body_parts),
                message_type="comment",
            )

        # Post individual messages on each budget.project
        for line in project_lines:
            line.budget_project_id.message_post(
                body=line._message_link_back_from_budget_project(),
                message_type="comment",
            )

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)
