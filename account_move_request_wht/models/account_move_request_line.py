from odoo import api, fields, models


class AccountMoveRequestLine(models.Model):
    _inherit = "account.move.request.line"

    wht_tax_id = fields.Many2one(
        comodel_name="account.withholding.tax",
        string="WHT",
        compute="_compute_wht_tax_id",
        store=True,
        readonly=False,
        check_company=True,
    )

    @api.depends("product_id", "request_id.partner_id")
    def _compute_wht_tax_id(self):
        for line in self:
            if line.product_id:
                partner = line.request_id.partner_id
                if partner and partner.company_type == "company":
                    line.wht_tax_id = line.product_id.supplier_company_wht_tax_id
                else:
                    line.wht_tax_id = line.product_id.supplier_wht_tax_id
            else:
                line.wht_tax_id = False
