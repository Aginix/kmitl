import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    READONLY_STATES = {
        "reserved": [("readonly", True)],
        "partial": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan",
        states=READONLY_STATES,
    )

    def _get_open_downstream_documents(self):
        """A live procurement plan owns its reservation: it blocks
        กลับแบบร่าง and ลบใบจอง."""
        documents = super()._get_open_downstream_documents()
        plan = self.sudo().procurement_plan_id
        if plan and plan.state not in ("done", "cancel"):
            documents.append(_("แผนจัดซื้อจัดจ้าง %s") % plan.display_name)
        return documents

    def action_view_procurement_plan(self):
        self.ensure_one()
        if not self.procurement_plan_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "type": "ir.actions.act_window",
            "res_model": "procurement.plan",
            "view_mode": "form",
            "res_id": self.procurement_plan_id.id,
            "target": "current",
        }
