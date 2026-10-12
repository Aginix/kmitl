from odoo import _, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def action_direct_allocation(self):
        """Open the จัดสรรและจองงบประมาณ wizard (Direct Allocation, ADR-0009)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("จัดสรรและจองงบประมาณ"),
            "res_model": "kmitl.project.direct.allocation",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }
