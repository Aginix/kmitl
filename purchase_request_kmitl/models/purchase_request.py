from datetime import datetime

from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

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
    attachment_ids = fields.One2many(
        comodel_name="purchase.request.attachment",
        inverse_name="request_id",
        string="Attachments",
        copy=True,
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

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "to_approve",
                "approved",
                "in_progress",
                "rejected",
                "done",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

