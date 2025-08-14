from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class PurchaseRequestTwoSubmittedLine(models.Model):
    _name = 'purchase.request.two.submitted.line'
    _description = 'PurchaseRequestTwoSubmittedLine'

    name = fields.Char('Name')

    submitted_id = fields.Many2one('purchase.request.two.submitted', string='Submitted')
    pr2_form_id = fields.Many2one('purchase.request.two', string='PR2 Form', required=True)
    vendor = fields.Many2one(related='pr2_form_id.vendor', string='Vendor', store=True, readonly=True)
    payment_type = fields.Selection(related='pr2_form_id.payment_type', string='Payment Type', store=True, readonly=True)
    department_id = fields.Many2one(related='pr2_form_id.department_id', store=True, string='Department', readonly=True)

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    purchase_request_name = fields.Char(related='pr2_form_id.purchase_request_name', string='Purchase request name', store=True, readonly=True)

    estimated_cost_from_pr = fields.Monetary(related='pr2_form_id.estimated_cost_from_pr', string="PR1 Total price", store=True, readonly=True, currency_field="currency_id")

    pr1_requested_by = fields.Many2one('res.users', related='pr2_form_id.pr1_requested_by', string='PR1 Requester', readonly=True, store=True)

    line_count = fields.Integer(
        string="Total Lines in Submitted",
        compute="_compute_line_count",
        store=True
    )
    payment_type_ref = fields.Selection(
        related='submitted_id.payment_type_ref',
        store=True,
        readonly=True
    )

    department_id_ref = fields.Many2one(
        'hr.department',
        related='submitted_id.department_id_ref',
        store=True,
        readonly=True
    )

    @api.depends('submitted_id.line_ids')
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.submitted_id.line_ids)


    @api.constrains('submitted_id', 'pr2_form_id')
    def _check_duplicate_pr2_form(self):
        for rec in self:
            if rec.submitted_id and rec.pr2_form_id:
                duplicates = rec.submitted_id.line_ids.filtered(
                    lambda line: line.pr2_form_id == rec.pr2_form_id and line.id != rec.id
                )
                if duplicates:
                    raise ValidationError("PR2 Form นี้ถูกเลือกไปแล้วในรายการนี้")