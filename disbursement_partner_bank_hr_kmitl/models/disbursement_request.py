# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    partner_is_internal = fields.Boolean(
        compute="_compute_partner_is_internal",
        string="Partner Is Internal Staff",
    )

    @api.depends("partner_id.partner_type_id.is_internal")
    def _compute_partner_is_internal(self):
        for line in self:
            line.partner_is_internal = bool(line.partner_id.partner_type_id.is_internal)
