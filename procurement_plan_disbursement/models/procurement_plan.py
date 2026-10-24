from odoo import _, api, fields, models

# Not cancelled and not yet settled: still holds the plan open (ค้าง).
DISBURSEMENT_OPEN_DOMAIN = [
    ("state", "!=", "cancel"),
    ("settlement_stage", "not in", ("settled", "booked")),
]


def _is_pending(dr):
    """Not cancelled, and its budget not consumed yet."""
    return dr.state != "cancel" and not dr.budget_consumed_amount


def _is_done(dr):
    """Not cancelled, and its budget consumed (money committed or paid out)."""
    return dr.state != "cancel" and dr.budget_consumed_amount > 0


class ProcurementPlan(models.Model):
    """Plan-side roll-up of the actual disbursement tracked per งวด. The plan is
    budget-control + tracking only — it authors no disbursement itself."""

    _inherit = "procurement.plan"

    disbursement_request_ids = fields.Many2many(
        comodel_name="disbursement.request",
        string="ใบขอเบิก",
        compute="_compute_disbursement_requests",
    )
    # Disbursements whose budget is not consumed yet.
    disbursement_pending_count = fields.Integer(
        string="จำนวนใบขอเบิก (รอดำเนินการ)",
        compute="_compute_disbursement_requests",
    )
    disbursement_pending_amount = fields.Monetary(
        string="ยอดรอดำเนินการ",
        compute="_compute_disbursement_requests",
        currency_field="currency_id",
    )
    # Disbursements whose budget the consume act has consumed (and what follows).
    disbursement_done_count = fields.Integer(
        string="จำนวนใบขอเบิก (ตัดงบแล้ว)",
        compute="_compute_disbursement_requests",
    )
    disbursement_done_amount = fields.Monetary(
        string="ยอดตัดงบแล้ว",
        compute="_compute_disbursement_requests",
        currency_field="currency_id",
    )
    amount_disbursed = fields.Monetary(
        string="เบิกจ่ายจริงรวม",
        compute="_compute_amount_disbursed",
        currency_field="currency_id",
        help="งบที่ตัดจริงรวมทุกงวด (นับเฉพาะใบขอเบิกที่ตัดงบประมาณแล้ว)",
    )

    @api.depends("payment_ids.disbursement_request_id")
    def _compute_disbursement_requests(self):
        for rec in self:
            # sudo so the counts/amounts show even to users who lack
            # disbursement.request read access — the check fires on click-through.
            drs = rec.payment_ids.mapped("disbursement_request_id").sudo()
            rec.disbursement_request_ids = drs
            pending = drs.filtered(_is_pending)
            done = drs.filtered(_is_done)
            rec.disbursement_pending_count = len(pending)
            rec.disbursement_pending_amount = sum(pending.mapped("amount_total"))
            rec.disbursement_done_count = len(done)
            rec.disbursement_done_amount = sum(done.mapped("amount_total"))

    @api.depends("payment_ids.amount_actual")
    def _compute_amount_disbursed(self):
        for rec in self:
            rec.amount_disbursed = sum(rec.payment_ids.mapped("amount_actual"))

    def action_view_pending_disbursement_requests(self):
        self.ensure_one()
        pending = self.disbursement_request_ids.filtered(_is_pending)
        return {
            "name": _("ใบขอเบิก (รอดำเนินการ)"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "domain": [("id", "in", pending.ids)],
            "view_mode": "tree,form",
        }

    def action_view_done_disbursement_requests(self):
        self.ensure_one()
        done = self.disbursement_request_ids.filtered(_is_done)
        return {
            "name": _("ใบขอเบิก (ตัดงบแล้ว)"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "domain": [("id", "in", done.ids)],
            "view_mode": "tree,form",
        }

    def _get_open_downstream_documents(self):
        """An outstanding (ค้าง) disbursement drawing the plan's reservation
        keeps the plan from being closed or deleted (procurement_plan ADR-0005)."""
        res = super()._get_open_downstream_documents()
        count = (
            self.env["disbursement.request"]
            .sudo()
            .search_count(
                [("budget_commitment_id.procurement_plan_id", "=", self.id)]
                + DISBURSEMENT_OPEN_DOMAIN
            )
        )
        if count:
            res.append(_("ใบขอเบิกที่ค้างดำเนินการอยู่ %s รายการ") % count)
        return res
