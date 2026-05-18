from odoo import api, fields, models, tools, _


class ApprovalRequestLine(models.Model):
    _name = "approval.request.line"
    _description = "Approval Request Line"

    sequence = fields.Integer(
        string="Sequence"
    )

    request_id = fields.Many2one(
        string="Request",
        comodel_name="approval.request",
        required=True
    )

    partner_id = fields.Many2one(
        string="Partner",
        comodel_name="res.partner",
        required=True
    )

    allowed_product_ids = fields.Many2many(
        string='Allowed Product IDs',
        compute='_compute_allowed_product_ids',
        comodel_name="product.product"
    )

    product_id = fields.Many2one(
        string="Expense",
        comodel_name="product.product",
        domain="[('id', 'in', allowed_product_ids)]",
        required=True
    )

    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        related="request_id.company_id",
    )

    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    total_amount = fields.Monetary(
        string="Total",
        currency_field='currency_id',
        required=True,
    )

    actual_amount = fields.Monetary(
        string="Actual amount",
        currency_field="currency_id",
    )

    @api.depends('request_id.category_id')
    def _compute_allowed_product_ids(self):
        for record in self:
            record.allowed_product_ids = record.request_id.category_id.allowed_product_ids
