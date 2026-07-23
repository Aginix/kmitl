from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _inherit = ["approval.request", "disbursement.return.source.mixin"]
    _disbursement_return_state = "billed"

    # -- return-correction editability (D3) --------------------------------
    def _compute_is_correction(self):
        """A returned request that already has a disbursement is a DR-return:
        only the recipient bank, description and disbursement evidence may be
        corrected (contrast a Sarabun return, which reopens the whole plan)."""
        super()._compute_is_correction()
        for rec in self:
            if rec.state == "returned" and rec.has_active_disbursement:
                rec.is_correction = True

    # -- return-to-source contract (disbursement.return.source.mixin) -----
    def _disbursement_get_request(self):
        self.ensure_one()
        return self._disbursement_pick_request(self.disbursement_request_ids)

    def _disbursement_apply_correction(self, dr):
        """Push the corrected recipient bank, description and disbursement
        evidence onto the still-signed DR. The banner/To-Do/state bookkeeping
        is handled generically by disbursement.request._apply_source_correction."""
        self.ensure_one()
        dr.note = self.description
        payee_bank = {
            alloc.partner_id.id: alloc.partner_bank_id.id
            for alloc in self.allocation_ids
            if alloc.partner_bank_id
        }
        for line in dr.line_ids:
            bank = payee_bank.get(line.partner_id.id)
            if bank:
                line.partner_bank_id = bank
        self._disbursement_copy_evidence(dr)

    def _disbursement_evidence_attachments(self):
        return self.disbursement_attachment_ids

    def _disbursement_correction_user(self):
        self.ensure_one()
        return self.user_id or self.create_uid

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

    @api.depends("disbursement_request_ids.state")
    def _compute_has_active_disbursement(self):
        for record in self:
            record.has_active_disbursement = any(
                d.state != "cancel" for d in record.disbursement_request_ids
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
            if not disbursements:
                record.billing_status = "no"
            elif all(d.state == "validated" for d in disbursements):
                record.billing_status = "full"
            elif any(d.state == "validated" for d in disbursements):
                record.billing_status = "partial"
            else:
                record.billing_status = "no"

    def write(self, vals):
        result = super().write(vals)
        if "disbursement_attachment_ids" in vals:
            self.disbursement_attachment_ids.filtered(
                lambda a: not a.is_disbursement_evidence
            ).write({"is_disbursement_evidence": True})
        return result

    def _billable_allocations(self):
        """Allocation rows that become disbursement lines — everything except
        `advance` (เงินยืม), which is money already lent and clears against the
        borrower's สัญญายืม instead of being disbursed again (ADR-0002)."""
        return self.allocation_ids.filtered(lambda a: a.payment_type != "advance")

    def _prepare_disbursement_request_vals(self):
        """Build a single multi-partner DR from the billable actual-expense
        allocation — one DR line per direct/prepaid row (recipient × product ×
        actual × bank); `advance` rows are excluded. The header carries
        `payment_type='direct'` as an interim: the DR module does not yet support
        mixed/per-line payment types, so direct and prepaid share one DR
        (ADR-0002)."""
        return {
            "reference": "approval.request,%d" % self.id,
            "approval_request_id": self.id,
            "partner_type": "multi",
            "payment_type": "direct",
            "line_ids": [
                Command.create(alloc._prepare_disbursement_request_line_vals())
                for alloc in self._billable_allocations()
            ],
            "ref": self.name,
            "note": self.description,
            "budget_commitment_id": self.budget_commitment_id.id,
            "budget_account_id": self.budget_account_id.id,
            "analytic_distribution": self.analytic_distribution,
        }

    def action_create_disbursement_request(self):
        self.ensure_one()
        if not self.allocation_ids:
            raise UserError(
                _("กรุณาบันทึกค่าใช้จ่ายจริงอย่างน้อย 1 รายการก่อนส่งเบิก")
            )
        self.action_bill()

        if not self._billable_allocations():
            # Every row is เงินยืม → nothing to disburse; those rows clear against
            # the สัญญายืม (deferred to the advance overhaul, ADR-0002). Bill the
            # request without creating an empty disbursement.
            self.message_post(
                body=_(
                    "ทุกรายการเป็นเงินยืม — ไม่ได้สร้างใบเบิก (รอเคลียร์กับสัญญายืม)"
                ),
                message_type="comment",
            )
            return True

        vals = self._prepare_disbursement_request_vals()
        disbursement = self.env["disbursement.request"].create(vals)
        self._copy_attachments_to_disbursement(disbursement)

        link = self._get_record_url()
        disbursement.message_post(
            body=_(
                'This record has been created from: '
                '<a href="%(link)s" target="_blank">%(name)s</a>',
                link=link,
                name=self.name,
            ),
            message_type="comment",
        )
        self.message_post(
            body=_(
                "Disbursement %(dr_name)s created successfully.",
                dr_name=disbursement.name,
            ),
            message_type="comment",
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "form",
            "res_id": disbursement.id,
            "target": "current",
        }

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

    def _copy_attachments_to_disbursement(self, disbursement):
        """Clone AR attachments to the given DR.

        Includes both the request-side attachment_ids (filtered to
        non-evidence on this model) and the disbursement_attachment_ids
        many2many that gathers DR-evidence files staged on the AR.

        Each clone gets its own ir.attachment row pointing at the same
        SHA1-hashed file in the Odoo filestore, so no binary is duplicated
        on disk.
        """
        self.ensure_one()
        attachments = self.attachment_ids | self.disbursement_attachment_ids
        for attachment in attachments:
            attachment.copy({
                "res_model": "disbursement.request",
                "res_id": disbursement.id,
            })

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)
