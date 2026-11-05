# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class DisbursementRequestSignature(models.Model):
    _inherit = "disbursement.request.signature"

    @api.model_create_multi
    def create(self, vals_list):
        signatures = super().create(vals_list)
        if not self.env.context.get("sarabun_defer_refreeze"):
            signatures.request_id._refreeze_sarabun_signed_pdf()
        return signatures

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals and not self.env.context.get("sarabun_defer_refreeze"):
            self.request_id._refreeze_sarabun_signed_pdf()
        return res
