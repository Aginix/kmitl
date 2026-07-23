from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


RETURNED_READONLY_STATES = {
    "to_verify": [("readonly", True)],
    "submitted": [("readonly", True)],
    "approved": [("readonly", True)],
    "ready_to_bill": [("readonly", True)],
    "billed": [("readonly", True)],
    "rejected": [("readonly", True)],
    "returned": [("readonly", True)],
}


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _inherit = ["approval.request", "disbursement.return.source.mixin"]
    _disbursement_return_state = "billed"

    state = fields.Selection(
        selection_add=[("returned", "Returned")],
        ondelete={"returned": "set default"},
    )

    # A returned request may correct ONLY the payee bank, description and
    # disbursement evidence. Lock every other normally-editable field by adding
    # 'returned' to their readonly states (only states= is overridden; the rest
    # of each field definition is inherited). description is intentionally left
    # editable in 'returned'.
    payment_type = fields.Selection(states=RETURNED_READONLY_STATES)
    category_id = fields.Many2one(states=RETURNED_READONLY_STATES)
    date = fields.Date(states=RETURNED_READONLY_STATES)
    owner_id = fields.Many2one(states=RETURNED_READONLY_STATES)
    date_start = fields.Date(states=RETURNED_READONLY_STATES)
    date_end = fields.Date(states=RETURNED_READONLY_STATES)
    city = fields.Char(states=RETURNED_READONLY_STATES)
    country_id = fields.Many2one(states=RETURNED_READONLY_STATES)

    @api.depends("state")
    def _compute_is_editable(self):
        """Keep a returned request non-editable at large; the correction fields
        are opened individually in the view instead."""
        super()._compute_is_editable()
        for rec in self:
            if rec.state == "returned":
                rec.is_editable = False

    # -- return-to-source contract (disbursement.return.source.mixin) -----
    def _disbursement_get_request(self):
        self.ensure_one()
        return self._disbursement_pick_request(self.disbursement_request_ids)

    def _disbursement_apply_correction(self, dr):
        """Push the corrected payee bank, description and disbursement evidence
        onto the still-signed DR. The banner/To-Do/state bookkeeping is handled
        generically by disbursement.request._apply_source_correction."""
        self.ensure_one()
        dr.note = self.description
        payee_bank = {
            payee.partner_id.id: payee.partner_bank_id.id
            for payee in self.payee_ids
            if payee.partner_bank_id
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

    def action_ready_to_bill(self):
        """Clerical staff marks a direct/prepaid request ready for the finance
        officer to bill. Requires at least one disbursement document."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(
                _("Only approved requests can be marked ready to bill.")
            )
        if self.payment_type not in ("direct", "prepaid"):
            raise UserError(
                _("Only direct or prepaid requests use the ready-to-bill step.")
            )
        if not self.disbursement_attachment_ids:
            raise UserError(
                _(
                    "Please attach at least one disbursement document before "
                    "marking this request ready to bill."
                )
            )
        self.state = "ready_to_bill"
        return True

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

    def _prepare_disbursement_request_vals(self):
        """Prepare vals for a single multi-partner DR from all approval lines."""
        return {
            "reference": "approval.request,%d" % self.id,
            "approval_request_id": self.id,
            "partner_type": "multi",
            "payment_type": self.payment_type,
            "line_ids": [
                Command.create(
                    {
                        **line._prepare_disbursement_request_line_vals(),
                        "partner_id": line.partner_id.id,
                    }
                )
                for line in self.line_ids
            ],
            "ref": self.name,
            "note": self.description,
            "budget_commitment_id": self.budget_commitment_id.id,
            "budget_account_id": self.budget_account_id.id,
            "analytic_distribution": self.analytic_distribution,
        }

    def action_create_disbursement_request(self):
        self.ensure_one()
        self.action_bill()
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
