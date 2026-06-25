from odoo import fields, models


class KrisProjectExpenseType(models.Model):
    _name = "kris.project.expense.type"
    _description = "KRIS Project Expense Type"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
    category_ids = fields.Many2many(
        comodel_name="kris.project.category",
        relation="kris_project_expense_type_category_rel",
        column1="expense_type_id",
        column2="category_id",
        string="Project Categories",
        help="Project categories this expense type applies to. "
        "Leave empty to apply to all categories.",
    )


class KrisProjectExpenseLine(models.Model):
    _name = "kris.project.expense.line"
    _description = "KRIS Project Expense Line"
    _order = "sequence, id"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    expense_type_id = fields.Many2one(
        comodel_name="kris.project.expense.type",
        string="Expense Type",
        required=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    amount = fields.Monetary(string="Amount", default=0.0)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        readonly=True,
    )
