import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    budget_project_ids = fields.One2many(
        comodel_name="budget.project",
        inverse_name="kmitl_project_id",
        string="การกันเงินงบประมาณ",
    )

    def _compute_is_editable(self):
        super()._compute_is_editable()
        for rec in self:
            if rec.budget_project_ids:
                rec.is_editable = False

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)
