from datetime import datetime

from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"


    _STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("validation", "Validated"),
    ("approved", "Approved"),
    ("done", "Done"),
    ("rejected", "Rejected"),
    ]

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
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
    tor_document_ids = fields.One2many(
        comodel_name="purchase.request.attachment",
        inverse_name="request_id",
        string="TOR",
        domain=[("attachment_type", "=", "tor")],
    )
    rfq_attachment_ids = fields.One2many(
        comodel_name="purchase.request.attachment",
        inverse_name="request_id",
        string="RFQ",
        domain=[("attachment_type", "=", "rfq")],
    )
    etc_document_ids = fields.One2many(
        comodel_name="purchase.request.attachment",
        inverse_name="request_id",
        string="ETC",
        domain=[("attachment_type", "=", "etc")],
    )
    title = fields.Char(
        string="title",
        required=True
    )
    description = fields.Text(string="reason", required=True)
    current_user = fields.Many2one(
        'res.users',
        string="Current User",
        compute='_compute_current_user',
        store=True,
    )
    is_current_user_requester = fields.Boolean(
        string="Is Current User Requester",
        compute="_compute_is_current_user_requester",
        store=False,
    )
    payment_type = fields.Selection([
        ("direct", "Direct paid"),
        ("loan", "Loan"),
        ("prepaid", "Prepaid")
    ])
    contract_type = fields.Selection([
        ('order', 'Purchase/Hire Order'),
        ('contract_buy', 'Contract buy'),
        ('contract_construction', 'Contract construction'),
    ], string="Contract type", required=True)
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        related="requested_by.employee_ids.department_id",
        store=True,
        readonly=True,
    )
    validated_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    date_validated = fields.Date(
        string="validate Date",
        copy=False,
    )
    @api.depends('requested_by')
    def _compute_is_current_user_requester(self):
        current_uid = self.env.uid
        for rec in self:
            rec.is_current_user_requester = rec.requested_by.id == current_uid

    @api.depends_context('uid')
    def _compute_current_user(self):
        for rec in self:
            rec.current_user = self.env.user

    def button_validate(self):
        return self.write({"state": "validation", "validated_by": self.env.user.id,"date_validated": fields.Date.context_today(self)})

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "to_approve",
                "validation",
                "approved",
                "rejected",
                "done",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def button_draft(self):
        self.write({"verified_by": "", "date_verified": False, "approved_by": "", "date_approved": False, "validated_by": "", "date_validated": False})
        return super().button_draft()
