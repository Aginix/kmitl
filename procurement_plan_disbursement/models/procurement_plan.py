from odoo import _, api, fields, models


class ProcurementPlan(models.Model):
    """Plan-side roll-up of the actual disbursement tracked per งวด. The plan is
    budget-control + tracking only — it authors no disbursement itself."""

    _inherit = "procurement.plan"

    disbursement_request_ids = fields.Many2many(
        comodel_name="disbursement.request",
        string="ใบขอเบิก",
        compute="_compute_disbursement_requests",
    )
    disbursement_request_count = fields.Integer(
        string="จำนวนใบขอเบิก", compute="_compute_disbursement_requests"
    )
    amount_disbursed = fields.Monetary(
        string="เบิกจ่ายจริงรวม",
        compute="_compute_amount_disbursed",
        currency_field="currency_id",
        help="งบที่ตัดจริงรวมทุกงวด (นับเฉพาะใบขอเบิกที่อนุมัติแล้ว)",
    )

    @api.depends("payment_ids.disbursement_request_id")
    def _compute_disbursement_requests(self):
        for rec in self:
            drs = rec.payment_ids.mapped("disbursement_request_id")
            rec.disbursement_request_ids = drs
            rec.disbursement_request_count = len(drs)

    @api.depends("payment_ids.amount_actual")
    def _compute_amount_disbursed(self):
        for rec in self:
            rec.amount_disbursed = sum(rec.payment_ids.mapped("amount_actual"))

    def action_view_disbursement_requests(self):
        self.ensure_one()
        return {
            "name": _("ใบขอเบิก"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "domain": [("id", "in", self.disbursement_request_ids.ids)],
            "view_mode": "tree,form",
        }
