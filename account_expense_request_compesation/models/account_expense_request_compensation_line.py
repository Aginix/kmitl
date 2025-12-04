from odoo import _, api, fields, models


class AccountExpenseRequestCompensationLine(models.Model):
    _name = "account.expense.request.compensation.line"
    _inherit = ["account.expense.request.line"]
    _description = "Account Expense Request Compensation Line"

    request_id = fields.Many2one(
        string="Request",
        comodel_name="account.expense.request.compensation",
        required=True
    )

    allowed_product_ids = fields.Many2many(
        string='Allowed Product IDs',
        compute='_compute_allowed_product_ids',
        comodel_name="product.product"
    )

    product_id = fields.Many2one(
        domain="[('id','in',allowed_product_ids)]"
    )

    @api.depends('request_id.compensation_type_id')
    def _compute_allowed_product_ids(self):
        for record in self:
            record.allowed_product_ids = record.request_id.compensation_type_id.allowed_expense_product_ids
