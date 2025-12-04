from odoo import _, fields, models


class AccountExpenseRequestAbstract(models.AbstractModel):
    _name = "account.expense.request.line"
    _inherit = ["analytic.mixin"]
    _description = "Account Expense Request Line Abstract"

    sequence = fields.Integer(
        string="Sequence",
        default=1,
    )

    partner_id = fields.Many2one(
        string='Partner',
        comodel_name="res.partner",
        required=True,
        domain="[('is_company', '=', False)]"
    )

    product_id = fields.Many2one(
        string="Expense",
        comodel_name="product.product",
        required=True
    )

    description = fields.Text(
        string="Description"
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,

    )

    amount_total = fields.Monetary(
        string="Amount Total",
        currency_field="currency_id",
        required=True,
    )
