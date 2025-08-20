from odoo import _, api, fields, models


class PurchaseRequestTwoSubmitted(models.Model):
    _name = 'purchase.request.two.submitted'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PurchaseRequestTwoSubmitted'

    _STATES = [
    ("draft", "Draft"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ]

    name = fields.Char(string='Submitted Ref', required=True, default=lambda self: _('New'))
    generate_po = fields.Boolean(string='Generate Purchase Order?', default=False)
    purchase_order_id = fields.Many2one('purchase.order', string='Linked Purchase Order', readonly=True)
    line_ids = fields.One2many('purchase.request.two.submitted.line', 'submitted_id', string="PR2 Forms")
    payment_type_ref = fields.Selection(
        [("direct", "Direct paid"),("loan", "Loan"),("prepaid", "Prepaid")],
        string="Reference Payment Type",
        compute="_compute_payment_type_ref",
        store=True,
    )
    department_id_ref = fields.Many2one(
        'hr.department',
        string='Department from PR2',
        compute='_compute_payment_type_ref',
        store=True
    )
    request_by = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
    )
    approval_date = fields.Date(
        string="Approve date",
        help="The date when the purchase order was approved. If not set, it will be the current date.",
    )
    approval_by = fields.Many2one(
        "res.users",
        string="Approve by",
        help="The user who approved the purchase order. If not set, it will be the current user.",
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    state = fields.Selection(selection=_STATES, default='draft', tracking=True)
    is_current_user_requester = fields.Boolean(
        string="Is Current User Requester",
        compute="_compute_is_current_user_requester",
        store=False,
    )

    @api.depends('request_by')
    def _compute_is_current_user_requester(self):
        current_uid = self.env.uid
        for rec in self:
            rec.is_current_user_requester = rec.request_by.id == current_uid

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
        self.approval_by = False
        self.approval_date = False
        self.state = 'draft'

    def button_approved(self):
        for line in self.line_ids:
            line.pr2_form_id.state = 'approved'
        self.approval_by = self.env.user.id
        self.approval_date = fields.Date.context_today(self)
        self.state = 'approved'

    def button_rejected(self):
        for line in self.line_ids:
            line.pr2_form_id.state = 'rejected'
        self.state = 'rejected'

    @api.depends('line_ids.pr2_form_id.payment_type')
    def _compute_payment_type_ref(self):
        for rec in self:
            first_line = rec.line_ids.filtered(lambda l: l.pr2_form_id.payment_type and l.pr2_form_id.department_id)
            rec.payment_type_ref = first_line[0].pr2_form_id.payment_type if first_line else False
            rec.department_id_ref = first_line[0].pr2_form_id.department_id if first_line else False
