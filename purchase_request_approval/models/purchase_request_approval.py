from odoo import _, api, fields, models


class PurchaseRequestApproval(models.Model):
    _name = 'purchase.request.approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Request Approval'

    _STATES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
    ]

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New')
    request_id = fields.Many2one(
        'purchase.request',
        string='PR1',
        readonly=True
    )
    vendor = fields.Many2one(
        "res.partner",
        string="Vendor",
        help="Select a vendor to create a purchase Request for the selected request lines.",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True
    )
    start_date = fields.Date(
        string="Start date",
        help="The start date for the purchase Request. If not set, the current date will be used.",
        tracking=True
    )
    end_date = fields.Date(
        string="End date",
        help="The end date for the purchase Request. If not set, the start date will be used.",
        tracking=True
    )
    purchase_request_number = fields.Char(
        string="Purchase request number",
        required=True,
        help="The number of the purchase request associated with the selected lines.",
    )
    contract_type = fields.Selection(
        related='request_id.contract_type',
        string="Contract type",
        store=True,
        readonly=True
    )
    payment_type = fields.Selection(
        related='request_id.payment_type', store=True, string="Payment type", readonly=True)
    purchase_request_name = fields.Char(
        string="Purchase request name",
        help="The name of the purchase request associated with the selected lines.",
        tracking=True
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
        tracking=True
    )
    line_ids = fields.One2many('purchase.request.approval.line', 'approval_id', string='Products', tracking=True)
    state = fields.Selection(selection=_STATES, default='draft', string='Status', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', compute='_compute_amount', store=True)
    amount_tax = fields.Monetary(string='Tax', compute='_compute_amount', store=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount', store=True)
    requested_by = fields.Many2one(
        'res.users',
        related='request_id.requested_by',
        string="Request By",
        store=True,
        readonly=True)
    estimated_cost = fields.Monetary(
        string="Total price",
        related='request_id.estimated_cost',
        readonly=True,
        store=True,
        currency_field="currency_id"
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='request_id.department_id',
        store=True,
        readonly=True,
    )
    master_department_id = fields.Many2one(
        'hr.department',
        related='request_id.department_id.master_department_id',
        store=True,
        readonly=True
    )
    is_egp = fields.Boolean(
        string="Over 100,000",
        compute="_compute_is_egp",
    )

    @api.depends("estimated_cost")
    def _compute_is_egp(self):
        for rec in self:
            rec.is_egp = rec.estimated_cost > 100000 if rec.estimated_cost else False

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "submitted",
                "cancçelled",
                "approved",
                "rejected",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def button_submit(self):
        return self.write({'state': 'submitted'})

    def button_cancel(self):
        return self.write({'state': 'cancelled'})

    def button_approve(self):
        return self.write({'state': 'approved'})

    def button_draft(self):
        self.write({'state': 'draft'})

    def button_reject(self):
        self.write({'state': 'rejected'})

    @api.depends('line_ids.quantity', 'line_ids.unit_price', 'line_ids.taxes')
    def _compute_amount(self):
        for rec in self:
            untaxed = 0.0
            taxes = 0.0
            currency = rec.currency_id
            for line in rec.line_ids:
                subtotal = line.quantity * line.unit_price
                tax_amount = sum(
                    tax._compute_amount(subtotal, 1, product=line.product_id, partner=rec.vendor)
                    for tax in line.taxes
                )
                untaxed += subtotal
                taxes += tax_amount
            rec.amount_untaxed = untaxed
            rec.amount_tax = taxes
            rec.amount_total = untaxed + taxes

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.approval') or _('New')
        return super().create(vals_list)

