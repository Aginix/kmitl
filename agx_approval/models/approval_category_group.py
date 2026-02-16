from odoo import api, fields, models, tools, _


class ApprovalCategoryGroup(models.Model):
    _name = "approval.category.group"
    _description = "Approval Category Group"

    name = fields.Char(
        string="Name",
        required=True
    )

    sequence = fields.Integer(
        string="Sequence"
    )
