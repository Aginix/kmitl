from datetime import datetime

from odoo import api, fields, models


class Purchase_request(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'base.exception']


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

    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="Purchase Type",
        ondelete="restrict",
        index=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
    to_create = fields.Selection(
        related="purchase_type_id.to_create",
    )
    procurement_method_ids = fields.Many2many(
        related="purchase_type_id.procurement_method_ids",
    )
    expense_reason = fields.Text(
        string="Reason",
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
    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
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

    source_of_fund = fields.Char(string="Source of fund")

    plan = fields.Char(string="Plan")

    fund = fields.Char(string="Fund")

    budget_type = fields.Char(string="Budget Type")

    expense_code = fields.Char(string="Expense code")

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

    @api.depends('requested_by')
    def _compute_is_current_user_requester(self):
        current_uid = self.env.uid
        for rec in self:
            rec.is_current_user_requester = rec.requested_by.id == current_uid

    @api.depends_context('uid')
    def _compute_current_user(self):
        for rec in self:
            rec.current_user = self.env.user

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

    has_finance_group = fields.Boolean(compute='_compute_has_finance_group')

    def button_validate(self):
        return self.write({"state": "validation", "validated_by": self.env.user.id, "date_validated": fields.Date.context_today(self)})

    def _get_domain_purchase_type(self):
        return [("visible_on_purchase_request", "=", True)]

    @api.onchange("purchase_type_id")
    def _onchange_purchase_type_id(self):
        procurement_methods = self.purchase_type_id.procurement_method_ids
        self.update(
            {
                "procurement_method_id": len(procurement_methods) == 1
                and procurement_methods.id
                or False,
            }
        )

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

    @api.depends_context('uid')
    def _compute_has_finance_group(self):
        allowed = self.env.user.has_group('kmitl_purchase_request_substate.group_purchase_request_substate_manager')
        for rec in self:
            rec.has_finance_group = allowed
