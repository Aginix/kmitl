# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class WithholdingTaxCert(models.Model):
    _inherit = "withholding.tax.cert"

    remittance_id = fields.Many2one(
        comodel_name="withholding.tax.remittance",
        string="WHT Remittance",
        ondelete="set null",
        copy=False,
    )
    remit_state = fields.Selection(
        selection=[("pending", "ยังไม่นำส่ง"), ("remitted", "นำส่งแล้ว")],
        string="Remittance Status",
        compute="_compute_remit_state",
        store=True,
    )
    amount_total = fields.Monetary(
        string="Tax Total",
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("remittance_id.state")
    def _compute_remit_state(self):
        for rec in self:
            rec.remit_state = (
                "remitted" if rec.remittance_id.state == "posted" else "pending"
            )

    @api.depends("wht_line.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.wht_line.mapped("amount"))

    def action_create_remittance(self):
        Remittance = self.env["withholding.tax.remittance"]
        Remittance._validate_certs(self)
        remittance = Remittance.create(
            {
                "income_tax_form": self[0].income_tax_form,
                "cert_ids": [(6, 0, self.ids)],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("WHT Remittance"),
            "res_model": "withholding.tax.remittance",
            "view_mode": "form",
            "res_id": remittance.id,
            "target": "current",
        }
