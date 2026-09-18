from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestApproval(models.Model):
    _name = "purchase.request.approval"
    _inherit = ["purchase.request.approval", "disbursement.return.source.mixin"]
    _disbursement_return_state = "approved"

    state = fields.Selection(
        selection_add=[("returned", "Returned")],
        ondelete={"returned": "set default"},
    )
    disbursement_return_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="purchase_request_approval_dr_return_attachment_rel",
        column1="approval_id",
        column2="attachment_id",
        string="Correction Evidence",
        copy=False,
    )

    contract_mode = fields.Selection(
        selection=[
            ("with_po", "Create Contract / Purchase Order"),
            ("no_po", "No Contract / Purchase Order"),
        ],
        string="Contract Mode",
        tracking=True,
        copy=False,
    )

    use_purchase_order = fields.Boolean(
        string="Use Purchase Order",
        compute="_compute_use_purchase_order",
        inverse="_inverse_use_purchase_order",
        store=True,
        tracking=True,
    )

    @api.depends("contract_mode")
    def _compute_use_purchase_order(self):
        for rec in self:
            rec.use_purchase_order = rec.contract_mode == "with_po"

    def _inverse_use_purchase_order(self):
        for rec in self:
            rec.contract_mode = "with_po" if rec.use_purchase_order else "no_po"

    def _check_contract_mode_selected(self):
        for rec in self:
            if not rec.contract_mode:
                raise UserError(
                    _(
                        "Please select 'Contract Mode' "
                        "(Create Contract / Purchase Order, or No Contract) "
                        "before proceeding."
                    )
                )

    def button_to_approve(self):
        self._check_contract_mode_selected()
        return super().button_to_approve()

    def action_submit_to_sarabun(self):
        self._check_contract_mode_selected()
        return super().action_submit_to_sarabun()

    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        compute="_compute_purchase_order_id",
        string="Purchase Order",
        store=True,
    )

    display_purchase_order = fields.Char(
        string="Purchase Order", compute="_compute_display_purchase_order", store=False
    )

    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="purchase_request_approval_id",
        string="Disbursement Requests",
    )

    billing_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Billing Status",
        compute="_compute_billing_status",
        store=True,
        tracking=True,
    )

    disbursement_request_count = fields.Integer(
        string="Disbursement Request Count",
        compute="_compute_disbursement_request",
    )

    disbursement_request_total = fields.Monetary(
        string="Total Disbursement Request",
        compute="_compute_disbursement_request",
        currency_field="currency_id",
        store=False,
    )

    purchase_count = fields.Integer(
        related="request_id.purchase_count",
        store=False,
    )

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)

    def button_approved(self):
        res = super().button_approved()
        for rec in self:
            if not rec.use_purchase_order:
                rec.request_id.button_done()
        return res

    def approval_make_purchase_order(self):
        res = self.request_id.approval_make_purchase_order()
        self.request_id.button_done()
        return res

    def action_view_purchase_order(self):
        return self.request_id.action_view_purchase_order()

    @api.depends("disbursement_request_ids", "disbursement_request_ids.amount_total")
    def _compute_disbursement_request(self):
        for approval in self:
            approval.disbursement_request_total = sum(
                approval.disbursement_request_ids.mapped("amount_total")
            )
            approval.disbursement_request_count = len(approval.disbursement_request_ids)

    # Vocabulary read off disbursement.request.state — never pipeline_status,
    # which lives on a different field and was never reachable from here.
    # bills_posted/payment_*/cleared are added by disbursement_accounting_kmitl
    # and disbursement_finance_kmitl via selection_add; if neither bridge is
    # installed a request simply never reaches those keys and stays
    # "in_progress" once approved, which is correct.
    _DR_STATE_TO_BILLING_STATUS = {
        "draft": "draft",
        "submitted": "submitted",
        "signed": "submitted",
        "verified": "submitted",
        "approved": "in_progress",
        "bills_posted": "in_progress",
        "payment_audited": "in_progress",
        "payment_authorized": "in_progress",
        "paid": "in_progress",
        "cleared": "done",
    }
    _BILLING_STATUS_RANK = {"draft": 0, "submitted": 1, "in_progress": 2, "done": 3}

    @api.depends("disbursement_request_ids", "disbursement_request_ids.state")
    def _compute_billing_status(self):
        for approval in self:
            active = approval.disbursement_request_ids.filtered(
                lambda r: r.state != "cancel"
            )
            if not approval.disbursement_request_ids:
                approval.billing_status = "draft"
            elif not active:
                approval.billing_status = "cancel"
            else:
                # Reflect the least-advanced request: the source document is
                # only as far along as its slowest disbursement request, not
                # whichever one happens to be first in the recordset.
                statuses = [
                    self._DR_STATE_TO_BILLING_STATUS.get(r.state, "draft")
                    for r in active
                ]
                approval.billing_status = min(
                    statuses, key=self._BILLING_STATUS_RANK.get
                )

    # -- return-to-source contract (disbursement.return.source.mixin) -----
    def _disbursement_get_request(self):
        self.ensure_one()
        return self._disbursement_pick_request(self.disbursement_request_ids)

    def _disbursement_evidence_attachments(self):
        return self.disbursement_return_attachment_ids

    def _prepare_disbursement_request_vals(self):
        return {
            "reference": "purchase.request.approval,%d" % self.id,
            "partner_id": self.partner_id.id,
            "partner_type": "multi",
            "line_ids": [
                Command.create(
                    {
                        **line._prepare_disbursement_request_line_vals(),
                        "partner_id": self.partner_id.id,
                    }
                )
                for line in self.request_id.line_ids
            ],
            "ref": self.request_id.name,
        }

    def action_view_disbursement_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "form,tree",
            "res_id": self.disbursement_request_ids.id,
            "target": "current",
        }

    def action_disbursement_request(self):
        self.ensure_one()
        disbursement_request = self._create_disbursement_request()
        return {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "form",
            "res_id": disbursement_request.id,
            "target": "current",
        }

    def _create_disbursement_request(self):
        disbursement_request = self.env["disbursement.request"].create(
            self._prepare_disbursement_request_vals()
        )
        link_back_message = disbursement_request._message_link_back_to_request()
        disbursement_request.message_post(
            body=link_back_message, message_type="comment"
        )
        message = self._purchase_request_approval_create_bill_message_content(
            disbursement_request
        )
        self.message_post(body=message, message_type="comment")
        self._post_message_to_purchase_request(disbursement_request)
        return disbursement_request

    def _post_message_to_purchase_request(self, disbursement_request):
        dr_link = (
            "/web#id=%d&model=disbursement.request&view_type=form"
            % disbursement_request.id
        )
        pa_link = "/web#id=%d&model=purchase.request.approval&view_type=form" % self.id
        self.request_id.message_post(
            body=_(
                'Disbursement Request <a href="%(dr_link)s" target="_blank">'
                "%(dr_name)s</a> has been created from Purchase Request Approval"
                ' <a href="%(pa_link)s" target="_blank">%(pa_name)s</a>.'
            )
            % {
                "dr_link": dr_link,
                "dr_name": disbursement_request.name,
                "pa_link": pa_link,
                "pa_name": self.name,
            },
            subtype_xmlid="mail.mt_note",
        )

    def _purchase_request_approval_create_bill_message_content(
        self, disbursement_request
    ):
        message = _(
            "Billing %(dr_name)s for %(pa_name)s created successfully, waiting for operation."
        ) % {
            "dr_name": disbursement_request.name,
            "pa_name": self.name,
        }

        return message

    @api.depends("request_id.line_ids.purchase_lines.order_id")
    def _compute_purchase_order_id(self):
        for rec in self:
            orders = rec.request_id.mapped("line_ids.purchase_lines.order_id")
            rec.purchase_order_id = orders[0] if orders else False

    @api.depends("use_purchase_order", "purchase_order_id.name")
    def _compute_display_purchase_order(self):
        for rec in self:
            if rec.use_purchase_order and rec.purchase_order_id:
                rec.display_purchase_order = rec.purchase_order_id.name
            elif not rec.use_purchase_order:
                rec.display_purchase_order = "ไม่ทำสัญญา"
            else:
                rec.display_purchase_order = ""
