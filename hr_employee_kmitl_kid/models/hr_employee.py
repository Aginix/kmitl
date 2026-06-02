import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    kid = fields.Char(
        string="KID",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _("New"),
    )

    _sql_constraints = [("unique_kid", "unique(kid)", "KID already exists!")]

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            val["kid"] = self.env["ir.sequence"].next_by_code("hr.employee.kmitl.kid")
        result = super(__class__, self).create(vals)
        return result
