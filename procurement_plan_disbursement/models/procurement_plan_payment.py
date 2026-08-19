from odoo import api, fields, models


class ProcurementPlanPayment(models.Model):
    """A งวด (installment) is manually linked to the disbursement request that
    pays it, so the plan can compare the planned tranche against the budget
    actually consumed. The link is authored here on the งวด line (never on the
    DR, which stays operational under the purchase order); 1 งวด → 1 DR."""

    _inherit = "procurement.plan.payment"

    currency_id = fields.Many2one(related="procurement_plan_id.currency_id")

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="ใบขอเบิก",
        copy=False,
        index=True,
        # Picker is domain-filtered in the view to DRs drawing this plan's
        # reservation down. No uniqueness constraint by design (kept loose).
        help="ใบขอเบิกที่จ่ายงวดนี้ — ผูกด้วยตนเองจากฝั่งแผน "
        "(การเบิกจ่ายจริงทำที่ใบสั่งซื้อ)",
    )
    disbursement_state = fields.Selection(
        related="disbursement_request_id.state",
        string="สถานะใบขอเบิก",
    )
    amount_actual = fields.Monetary(
        string="เบิกจ่ายจริง",
        compute="_compute_amount_actual",
        store=True,
        currency_field="currency_id",
        help="งบที่ตัดจริงของงวดนี้ = ยอด consumed ของใบขอเบิกเมื่ออนุมัติแล้ว "
        "(ใบขอเบิกที่ยังไม่อนุมัติถือเป็น 'กำลังดำเนินการ' ไม่นับ)",
    )

    @api.depends(
        "disbursement_request_id.state",
        "disbursement_request_id.budget_consumed_amount",
    )
    def _compute_amount_actual(self):
        for rec in self:
            dr = rec.disbursement_request_id
            # Only an approved DR has obligated+consumed the plan's budget; a
            # cancelled DR keeps a stale budget_consumed_amount, so gate on state.
            rec.amount_actual = (
                dr.budget_consumed_amount if dr and dr.state == "approved" else 0.0
            )
