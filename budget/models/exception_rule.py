from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    budget_selection_wizard_ids = fields.Many2many(
        comodel_name="budget.selection.wizard",
        string="Budget Selection Wizards",
    )
    model = fields.Selection(
        selection_add=[
            ("budget.selection.wizard", "Budget Selection Wizard"),
        ],
        ondelete={
            "budget.selection.wizard": "cascade",
        },
    )
