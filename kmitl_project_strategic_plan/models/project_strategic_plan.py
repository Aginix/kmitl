from odoo import api, models


class ProjectStrategicPlan(models.Model):
    _inherit = "project.strategic.plan"

    @api.onchange("parent_id")
    def _onchange_parent_id_level(self):
        if self.parent_id:
            self.level = self.parent_id.level
