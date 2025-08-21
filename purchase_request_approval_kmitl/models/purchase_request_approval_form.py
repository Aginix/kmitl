from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseRequestApprovalForm(models.Model):
    _name = 'purchase.request.approval.form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Purchase Request Approval Form'

    _STATES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("po_created", "PO Created"),
        ("rejected", "Rejected"),
    ]

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New')
    pr1_ref = fields.Many2one(
        'purchase.request',
        string='PR1 Reference',
        readonly=True
    )
    vendor = fields.Many2one(
        "res.partner",
        string="Vendor",
        help="Select a vendor to create a purchase order for the selected request lines.",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True
    )
    start_date = fields.Date(
        string="Start date",
        help="The start date for the purchase order. If not set, the current date will be used.",
        tracking=True
    )
    end_date = fields.Date(
        string="End date",
        help="The end date for the purchase order. If not set, the start date will be used.",
        tracking=True
    )
    purchase_request_number = fields.Char(
        string="Purchase request number",
        required=True,
        help="The number of the purchase request associated with the selected lines.",
    )
    contract_type = fields.Selection(
        related='pr1_ref.contract_type',
        string="Contract type",
        store=True,
        readonly=True
    )
    payment_type = fields.Selection(
        related='pr1_ref.payment_type', store=True, string="Payment type", readonly=True)
    purchase_request_name = fields.Char(
        string="Purchase request name",
        help="The name of the purchase request associated with the selected lines.",
        tracking=True
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    line_ids = fields.One2many('purchase.request.approval.form.line', 'pr2_id', string='Products', tracking=True)
    state = fields.Selection(selection=_STATES, default='draft', string='Status', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', compute='_compute_amount', store=True)
    amount_tax = fields.Monetary(string='Tax', compute='_compute_amount', store=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount', store=True)
    submitted_id = fields.Many2one('purchase.request.approval.submitted', string='PR2 Ref', readonly=True)
    submitted_state = fields.Selection(related='submitted_id.state', string='PR2 State')
    generate_po = fields.Boolean(string='Generate Purchase Order?', default=True, tracking=True)
    pr1_requested_by = fields.Many2one(
        'res.users',
        related='pr1_ref.requested_by',
        string="PR1 Requester",
        store=True,
        readonly=True)
    estimated_cost_from_pr = fields.Monetary(
        string="PR1 Total price",
        related='pr1_ref.estimated_cost',
        readonly=True,
        store=True,
        currency_field="currency_id"
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department (from PR1)',
        related='pr1_ref.department_id',
        store=True,
        readonly=True,
    )

    @api.constrains('start_date', 'end_date')
    def _check_end_date_within_30_days(self):
        for record in self:
            if record.start_date and record.end_date:
                diff_days = (record.end_date - record.start_date).days
                if diff_days > 30:
                    raise ValidationError(
                        "วันเริ่มและวันสิ้นสุดสัญญาต้องไม่เกิน 30 วัน"
                    )

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "submitted",
                "po_created",
                "approved",
                "rejected",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_egp(self):
        for rec in self:
            if rec.estimated_cost_from_pr < 100000:
                raise UserError("ยอดประมาณการจาก PR1 ยังไม่ถึง 100,000 บาท")
            rec.write({'state': 'approved'})

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

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.approval.form') or _('New')
        return super().create(vals)

    def action_merge_to_submitted(self):
        self.ensure_one()
        self.write({'state': 'submitted'})
        submitted = self.env['purchase.request.approval.submitted'].create({
            'name': self.env['ir.sequence'].next_by_code('purchase.request.approval.submitted'),
        })

        self.submitted_id = submitted.id
        self.env['purchase.request.approval.submitted.line'].create({
            'submitted_id': submitted.id,
            'pr2_form_id': self.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.approval.submitted',
            'view_mode': 'form',
            'res_id': submitted.id,
            'target': 'current',
        }

    def button_draft(self):
        self.write({'state': 'draft'})
