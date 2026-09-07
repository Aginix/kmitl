from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    partner_id_domain = fields.Binary(
        compute="_compute_partner_id_domain",
        readonly=True,
        store=False,
    )

    @api.depends("payment_type")
    def _compute_partner_id_domain(self):
        for rec in self:
            rec.partner_id_domain = []

    state = fields.Selection(
        selection_add=[
            ("to_submit", "To Submit"),
            ("to_approve",),
            ("cancelled", "Cancelled"),
            ("returned", "Returned"),
        ],
        ondelete={
            "to_submit": "set default",
            "cancelled": "set default",
            "returned": "set default",
        },
    )

    line_ids = fields.One2many(
        states={
            "draft": [("readonly", False)],
            "returned": [("readonly", False)],
        },
    )
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
    procurement_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Procurement Committees",
        domain=[("committee_type", "=", "procurement")],
        copy=True,
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Acceptance Committees",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
        tracking=True,
    )
    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
    )
    verified_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    date_verified = fields.Date(
        string="Verified Date",
        copy=False,
    )
    date_approved = fields.Date(
        string="Approved Date",
        copy=False,
    )
    partner_id = fields.Many2one("res.partner", tracking=True)

    # construction
    is_construction = fields.Boolean(string="Construction", readonly=True)
    title = fields.Char(string="Title", tracking=True)
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        default=lambda self: self._default_account_fiscal_year_id(),
    )

    @api.model
    def _default_account_fiscal_year_id(self):
        """ปีงบปัจจุบัน (ตามวันนี้) เป็นค่าตั้งต้น.

        ทุก flow ด้านงบใช้ปีงบนี้อยู่แล้ว (จอง/หยิบใบจอง/ออกเลขที่ พจ.) การเว้นว่างทำให้
        dropdown ใบจองที่กรองตามปีงบไม่ขึ้นรายการ และเลขที่ พจ. หล่นไปใช้ปีปฏิทินแทนปีงบ."""
        today = fields.Date.context_today(self)
        return self.env["account.fiscal.year"].search(
            [
                ("date_from", "<=", today),
                ("date_to", ">=", today),
                ("company_id", "in", [self.env.company.id, False]),
            ],
            limit=1,
        )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        domain=[("res_model", "=", "purchase.request")],
        string="Document Attachments",
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        copy=False,
        default=lambda self: self.env.user,
        index=True,
    )
    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="TOR Committees",
        domain=[("committee_type", "=", "tor_committee")],
        copy=True,
    )
    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Price Determine Committees",
        domain=[("committee_type", "=", "price_determine")],
        copy=True,
    )
    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Evaluation Committees",
        domain=[("committee_type", "=", "evaluation")],
        copy=True,
    )
    work_supervisor_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Supervisors",
        domain=[("committee_type", "=", "work_supervisor")],
        copy=True,
    )
    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")
    can_reset_to_draft = fields.Boolean(compute="_compute_can_reset_to_draft")

    @api.depends("state", "requested_by")
    def _compute_can_reset_to_draft(self):
        is_manager = self.env.user.has_group(
            "purchase_request.group_purchase_request_manager"
        )
        for rec in self:
            if rec.state == "to_approve":
                rec.can_reset_to_draft = is_manager
            elif rec.state in ("to_verify", "to_submit"):
                rec.can_reset_to_draft = is_manager or rec.requested_by == self.env.user
            else:
                rec.can_reset_to_draft = False

    @api.depends("state")
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = not (
                rec.state in ("approved", "in_progress") and rec.purchase_count == 0
            )

    def get_estimated_cost_currency(self, date=False):
        """Return the total estimated cost across all lines."""
        self.ensure_one()
        return sum(self.line_ids.mapped("estimated_cost"))

    def _apply_sarabun_approve_metadata(self):
        self.write(
            {
                "approved_by": self.env.user.id,
                "date_approved": fields.Date.context_today(self),
            }
        )

    def _transition_after_sarabun_approve(self):
        """Dispatch state transition after Sarabun completes routing.

        Overridden in purchase_request_egp (is_egp=True → in_egp) and
        purchase_request_approval (is_egp=False → in_approval + auto-PA).
        The base fallback writes 'approved' if neither branch is installed.
        """
        self._apply_sarabun_approve_metadata()
        self.write({"state": "approved"})

    def button_approved(self):
        self._apply_sarabun_approve_metadata()
        return super().button_approved()

    def button_to_submit(self):
        return self.write({"state": "to_submit"})

    def button_cancel(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ยกเลิกคำขอ (พ.1)"),
            "res_model": "purchase.request.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _action_do_cancel(self, reason):
        self.ensure_one()
        body = _("ยกเลิกคำขอ (พ.1) %(pr)s เหตุผล: %(reason)s") % {
            "pr": self.name,
            "reason": reason,
        }
        self.message_post(body=body, subtype_xmlid="mail.mt_note")
        self.write({"state": "cancelled"})

    def button_return(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ตีกลับคำขอ (พ.1)"),
            "res_model": "purchase.request.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _action_do_return(self, reason=None, post_message=True):
        self.ensure_one()
        if post_message:
            body = _(
                "ตีกลับคำขอ (พ.1) %(pr)s เหตุผล: %(reason)s"
            ) % {"pr": self.name, "reason": reason or ""}
            self.message_post(body=body, subtype_xmlid="mail.mt_note")
        self.write({"state": "returned"})

    def _action_do_return_to_draft(self, reason):
        self.ensure_one()
        body = _(
            "ตีกลับคำขอ (พ.1) %(pr)s เหตุผล: %(reason)s"
        ) % {"pr": self.name, "reason": reason}
        self.message_post(body=body, subtype_xmlid="mail.mt_note")
        return self.button_draft()
