# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        months = {(d.year, d.month) for d in self.mapped("date")}
        if len(months) > 1:
            raise UserError(
                _("Selected certificates span more than one month; group by month.")
            )
        year, month = months.pop()
        # _validate_certs ยืนยันแล้วว่าใบที่เลือกมีแหล่งเงินร่วมกันเพียงแหล่งเดียว
        source_ids = set()
        for cert in self:
            source_ids |= Remittance._cert_source_ids(cert)
        remittance = Remittance.create(
            {
                "income_tax_form": self[0].income_tax_form,
                "period_month": str(month),
                "period_year": str(year + 543),
                "source_analytic_id": source_ids.pop(),
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
