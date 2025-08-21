from odoo import _, api, fields, models


class PurchaseRequestApprovalSubmitted(models.Model):
    _name = 'purchase.request.approval.submitted'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Request Approval Submitted'

    _STATES = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    # past tense
    name = fields.Char(string='Submitted Ref', required=True, default=lambda self: _('New'))
    line_ids = fields.One2many('purchase.request.approval.submitted.line', 'submitted_id', string="PR2 Forms")
    payment_type = fields.Selection(
        [("direct", "Direct paid"),("loan", "Loan"),("prepaid", "Prepaid")],
        string="Payment Type",
        compute="_compute_payment_type",
        store=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        compute='_compute_payment_type',
        store=True
    )
    requested_by = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
    )
    approved_date = fields.Date(
        string="Approve date",
        help="The date when the purchase order was approved. If not set, it will be the current date.",
    )
    approved_by = fields.Many2one(
        "res.users",
        string="Approve by",
        help="The user who approved the purchase order. If not set, it will be the current user.",
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    state = fields.Selection(selection=_STATES, default='draft', tracking=True)
    is_current_user_request = fields.Boolean(
        string="Is Current User Requester",
        compute="_compute_is_current_user_request",
        store=False,
    )

    @api.depends('request_by')
    def _compute_is_current_user_request(self):
        current_uid = self.env.uid
        for rec in self:
            rec.is_current_user_request = rec.request_by.id == current_uid

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "approved",
                "rejected",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def button_draft(self):
        for line in self.line_ids:
            line.pr2_form_id.state = 'submitted'
        self.approved_by = False
        self.approved_date = False
        self.state = 'draft'

    def button_approved(self):
        for line in self.line_ids:
            line.pr2_form_id.state = 'approved'
        self.approved_by = self.env.user.id
        self.approved_date = fields.Date.context_today(self)
        self.state = 'approved'

    def button_rejected(self):
        for line in self.line_ids:
            line.pr2_form_id.state = 'rejected'
        self.state = 'rejected'

    # แยก
    @api.depends('line_ids.pr2_form_id.payment_type')
    def _compute_payment_type(self):
        for rec in self:
            first_line = rec.line_ids.filtered(lambda l: l.pr2_form_id.payment_type and l.pr2_form_id.department_id)
            rec.payment_type = first_line[0].pr2_form_id.payment_type if first_line else False
            rec.department_id = first_line[0].pr2_form_id.department_id if first_line else False
