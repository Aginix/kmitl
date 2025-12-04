from odoo import _, fields, models


class AccountExpenseRequestCompensationType(models.Model):

    _name = "account.expense.request.compensation.type"
    _description = "Account Expense Request Compensation Type"

    code = fields.Char(
        string="Code",
        required=True,
        copy=False
    )

    name = fields.Char(
        string="Name",
        required=True,
    )

    allowed_expense_product_ids = fields.Many2many(
        string="Allowed Expenses",
        comodel_name="product.product",
    )
