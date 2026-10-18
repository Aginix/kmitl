from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # A DR is "billed" once its budget has been committed at ``approved`` and
    # stays billed through every downstream state a finance/accounting bridge
    # may add (bills_posted, payment_*, paid, cleared) — those states are not
    # owned by this module and must never be enumerated here. Excluding the
    # states that precede budget commitment, plus ``cancel``, is the only
    # comparison that stays correct regardless of which bridges are installed.
    _DISBURSEMENT_NOT_BILLED_STATES = (
        "draft", "submitted", "signed", "verified", "cancel",
    )

    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="approval_request_id",
        string="Disbursement Requests",
    )

    disbursement_request_count = fields.Integer(
        string="Disbursement Request Count",
        compute="_compute_disbursement_request",
    )

    billing_status = fields.Selection(
        selection=[
            ("no", "Nothing to Bill"),
            ("partial", "Partially Billed"),
            ("full", "Fully Billed"),
        ],
        string="Billing Status",
        compute="_compute_billing_status",
        store=True,
        tracking=True,
    )

    attachment_ids = fields.One2many(
        domain=[("is_disbursement_evidence", "=", False)],
    )

    disbursement_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='approval_request_disbursement_attachment_rel',
        column1='request_id',
        column2='attachment_id',
        string='Disbursement Attachments',
    )

    has_active_disbursement = fields.Boolean(
        compute="_compute_has_active_disbursement",
    )

    disbursed_amount = fields.Monetary(
        string="ยอดตั้งเบิกแล้ว",
        currency_field="currency_id",
        compute="_compute_disbursed_amount",
        help="ยอดรวมใบขอเบิกที่ไม่ถูกยกเลิกของคำขอนี้ — ต้องไม่เกินยอดค่าใช้จ่ายจริง",
    )

    @api.depends("disbursement_request_ids.state")
    def _compute_has_active_disbursement(self):
        for record in self:
            record.has_active_disbursement = any(
                d.state != "cancel" for d in record.disbursement_request_ids
            )

    @api.depends(
        "disbursement_request_ids.state", "disbursement_request_ids.amount_total"
    )
    def _compute_disbursed_amount(self):
        for record in self:
            record.disbursed_amount = sum(
                record._active_disbursements().mapped("amount_total")
            )

    @api.depends("disbursement_request_ids")
    def _compute_disbursement_request(self):
        for record in self:
            record.disbursement_request_count = len(
                record.disbursement_request_ids
            )

    @api.depends("disbursement_request_ids", "disbursement_request_ids.state")
    def _compute_billing_status(self):
        for record in self:
            disbursements = record.disbursement_request_ids
            billed = disbursements.filtered(
                lambda d: d.state not in self._DISBURSEMENT_NOT_BILLED_STATES
            )
            if not disbursements or not billed:
                record.billing_status = "no"
            elif billed == disbursements:
                record.billing_status = "full"
            else:
                record.billing_status = "partial"

    def write(self, vals):
        result = super().write(vals)
        if "disbursement_attachment_ids" in vals:
            self.disbursement_attachment_ids.filtered(
                lambda a: not a.is_disbursement_evidence
            ).write({"is_disbursement_evidence": True})
        return result

    def _active_disbursements(self):
        self.ensure_one()
        return self.sudo().disbursement_request_ids.filtered(
            lambda d: d.state != "cancel"
        )

    @api.constrains("allocation_ids")
    def _check_actual_covers_disbursed(self):
        """The recorded actuals cap what finance may bill (ADR-0009), so they may
        not be lowered below what is already on non-cancelled ใบขอเบิก."""
        for rec in self:
            if rec.currency_id.compare_amounts(
                rec.total_actual_amount, rec.disbursed_amount
            ) < 0:
                raise ValidationError(
                    _(
                        "ยอดค่าใช้จ่ายจริง (%(actual)s) ต่ำกว่ายอดที่ตั้งเบิกแล้ว"
                        " (%(disbursed)s)"
                    )
                    % {
                        "actual": rec.total_actual_amount,
                        "disbursed": rec.disbursed_amount,
                    }
                )

    def action_create_disbursement_request(self):
        """Open a new ใบขอเบิก prefilled with this request's header only —
        finance enters recipients, items, amounts, banks and the payment type.
        May be pressed repeatedly: one request → many ใบขอเบิก (ADR-0009)."""
        self.ensure_one()
        if self.state != "to_disburse":
            raise UserError(
                _("สร้างใบขอเบิกได้เฉพาะสถานะ 'รอการเงินตรวจสอบ/ส่งเบิก'")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบขอเบิก"),
            "res_model": "disbursement.request",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_approval_request_id": self.id,
                "default_reference": "approval.request,%d" % self.id,
                "default_partner_type": "multi",
                "default_ref": self.name,
                "default_note": self.description,
                "default_budget_commitment_id": self.budget_commitment_id.id,
                "default_budget_account_id": self.budget_account_id.id,
                "default_analytic_distribution": self.analytic_distribution,
            },
        }

    def action_bill(self):
        """ตั้งเบิกครบแล้ว: finance closes billing. Unused reservation is not
        returned here — budget staff use คืนจอง on the ใบจองงบประมาณ."""
        for record in self:
            if not record._active_disbursements():
                raise UserError(
                    _("กรุณาสร้างใบขอเบิกอย่างน้อย 1 ใบก่อนกดตั้งเบิกครบแล้ว")
                )
        return super().action_bill()

    def action_pull_back_from_finance(self):
        for record in self:
            if record._active_disbursements():
                raise UserError(
                    _("ดึงกลับไม่ได้ เนื่องจากการเงินสร้างใบขอเบิกแล้ว")
                )
        return super().action_pull_back_from_finance()

    def action_view_disbursement_request(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "target": "current",
        }
        if len(self.disbursement_request_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.disbursement_request_ids.id
        else:
            action["view_mode"] = "tree,form"
            action["domain"] = [
                ("id", "in", self.disbursement_request_ids.ids)
            ]
        return action
