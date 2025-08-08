from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestTwo(models.Model):
    _name = 'purchase.request.two'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PurchaseRequestTwo'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New')

    pr1_ref = fields.Many2one(
        'purchase.request',
        string='อ้างอิง PR1',
        readonly=True
    )

    vendor = fields.Many2one(
        "res.partner",
        string="Vendor",
        help="Select a vendor to create a purchase order for the selected request lines.",
    )
    start_date = fields.Date(
        string="วันที่เริ่มสัญญา",
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    end_date = fields.Date(
        string="วันที่สิ้นสุดสัญญา",
        help="The end date for the purchase order. If not set, the start date will be used.",
    )
    purchase_request_number = fields.Char(
        string="หมายเลขคำสั่งซื้อ",
        required=True,
        help="The number of the purchase request associated with the selected lines.",
    )
    contract_type = fields.Selection(
        related='pr1_ref.contract_type',
        string="ประเภทสัญญา",
        store=True,
        readonly=True
    )

    payment_type = fields.Selection([
        ("direct", "จ่ายตรง"),
        ("loan", "เงินยืม"),
        ("prepaid", "สำรองจ่าย")
    ], string="ประเภทการจ่ายเงิน", readonly=True)

    purchase_request_name = fields.Char(
        string="ชื่อใบสั่งซื้อ/จ้าง",
        help="The name of the purchase request associated with the selected lines.",
    )

    line_ids = fields.One2many('purchase.request.two.line', 'pr2_id', string='Products')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('po_created', 'PO Created'),
        ('rejected', 'Rejected')
    ], default='draft', string='Status', tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    amount_untaxed = fields.Monetary(string='รวมเป็นเงิน', compute='_compute_amount', store=True)
    amount_tax = fields.Monetary(string='ภาษีมูลค่าเพื่ม', compute='_compute_amount', store=True)
    amount_total = fields.Monetary(string='รวมเป็นเงินทั้งสิ้น', compute='_compute_amount', store=True)

    submitted_id = fields.Many2one('purchase.request.two.submitted', string='Included in Submitted', readonly=True)

    generate_po = fields.Boolean(string='Generate Purchase Order?', default=True)

    estimated_cost_from_pr = fields.Monetary(
        string="ราคารวมจาก PR1",
        related='pr1_ref.estimated_cost',
        readonly=True,
        store=True,
        currency_field="currency_id"
    )

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
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.two.form') or _('New')
        return super().create(vals)

    def action_merge_to_submitted(self):
        self.write({'state': 'submitted'})
        self.ensure_one()

        submitted = self.env['purchase.request.two.submitted'].create({
            'name': self.env['ir.sequence'].next_by_code('purchase.request.two.submitted'),
        })

        self.submitted_id = submitted.id
        self.env['purchase.request.two.submitted.line'].create({
            'submitted_id': submitted.id,
            'pr2_form_id': self.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.two.submitted',
            'view_mode': 'form',
            'res_id': submitted.id,
            'target': 'current',
        }

    def button_draft(self):
        self.write({'state': 'draft'})

    def make_purchase_order(self):
        self.ensure_one()

        if not self.generate_po:
            return

        if self.state != 'approved':
            raise UserError("This PR2 is not ready for PO. Please approve first.")

        if not self.vendor:
            raise UserError("Vendor is required.")

        order_lines = []
        for line in self.line_ids:
            if not line.product_id or not line.quantity:
                raise UserError("Please fill all required line data.")
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.description or line.product_id.display_name,
                'product_qty': line.quantity,
                'price_unit': line.unit_price,
                'taxes_id': [(6, 0, line.taxes.ids)],
                'product_uom': line.product_id.uom_po_id.id,
            }))

        po = self.env['purchase.order'].create({
            'department_id': self.env.user.employee_id.department_id.id,
            'partner_id': self.vendor.id,
            'order_line': order_lines,
            'origin': self.name,
            'contract_type' : self.purchase_type,
            'contract_start_date': self.start_date,
            'contract_end_date': self.end_date,
            'purchase_request_name': self.purchase_request_name,
            'pr1_ref': self.pr1_ref.id,
            'pr2_ref': self.id,
        })

        self.state = 'po_created'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }
